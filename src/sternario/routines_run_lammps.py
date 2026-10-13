from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
from threading import Thread


# ===============================================================
# 1. SISTEMA DE STATUS
# ===============================================================
def build_status_name(condition: str, sim_id: int) -> str:
    now = datetime.now()
    return (
        f"status_{condition}_sim{sim_id}_"
        f"{now.day:02d}_{now.month:02d}_{now.year}_"
        f"{now.hour:02d}h_{now.minute:02d}min_{now.second:02d}s.txt"
    )


def create_status(sim_dir: Path, base_dir: Path, condition: str, filename: str):
    logs_map = {
        "in_progress": base_dir / "Logs" / "in_progress",
        "success": base_dir / "Logs" / "success",
        "error": base_dir / "Logs" / "error",
    }

    logs_target = logs_map[condition]
    logs_target.mkdir(parents=True, exist_ok=True)

    sim_file = sim_dir / filename
    log_file = logs_target / filename

    content = f"Caminho da simulação:\n{sim_dir}\n"

    with open(sim_file, "w", encoding="utf-8") as f:
        f.write(content)

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(content)


def remove_in_progress(sim_dir: Path, base_dir: Path, filename: str):
    try:
        sim_file = sim_dir / filename
        log_file = base_dir / "Logs" / "in_progress" / filename

        if sim_file.exists():
            sim_file.unlink()

        if log_file.exists():
            log_file.unlink()
    except Exception:
        pass


def has_success_status(sim_dir: Path) -> bool:
    return any("success" in f.name for f in sim_dir.glob("status*.txt"))


# ===============================================================
# 2. VERIFICAÇÃO DA SIMULAÇÃO
# ===============================================================
def get_expected_steps(input_path: Path):
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.split("#")[0].strip()
                if clean_line.startswith("variable") and "nsteps" in clean_line:
                    match = re.search(r"nsteps\s+\w+\s+(\d+)", clean_line)
                    if match:
                        return int(match.group(1))
    except Exception:
        pass
    return None


def get_last_step(log_path: Path):
    try:
        with open(log_path, "rb") as f:
            f.seek(-4000, 2)
            tail = f.read().decode(errors="ignore")

        for line in reversed(tail.splitlines()):
            parts = line.strip().split()
            if parts and parts[0].isdigit():
                return int(parts[0])
    except Exception:
        pass
    return None


def simulation_ok(sim_dir: Path, log_file: str) -> bool:
    expected = get_expected_steps(sim_dir / "density.in")
    last = get_last_step(sim_dir / log_file)
    return expected is not None and last == expected


# ===============================================================
# 3. EXECUÇÃO DA SIMULAÇÃO (COM TERMINAIS VISÍVEIS)
# ===============================================================
def run_simulation_in_cmd(
    sim_dir: Path,
    base_dir: Path,
    lmp_bin_wsl: str,
    sim_id: int,
    use_gpu: bool,
    worker_name: str,
):
    if has_success_status(sim_dir):
        print(
            f"[{worker_name}] Simulação {sim_dir.name} já concluída com 'success'. Pulando."
        )
        return

    # Mapeamento do caminho Windows -> WSL POSIX (/mnt/d/...)
    drive_letter = sim_dir.drive[0].lower()
    path_without_drive = sim_dir.as_posix()[2:]
    wsl_dir_path = f"/mnt/{drive_letter}{path_without_drive}"

    sf_option = "gpu" if use_gpu else "omp"
    pk_option = "" if use_gpu else "-pk omp 12"
    log_file = f"log_{sf_option}_{worker_name}_sim{sim_id}.lammps"

    # Comando executado no Bash do WSL
    bash_script = (
        f"cd '{wsl_dir_path}' && "
        f"{lmp_bin_wsl} -in density.in -sf {sf_option} {pk_option} -log {log_file}"
    )

    # Título que aparecerá na barra da janela do CMD
    window_title = f"LAMMPS [{worker_name}] - Sim #{sim_id}: {sim_dir.name}"

    # Monta o comando do Windows para ABRIR o CMD visível e esperá-lo fechar (/wait)
    cmd = f'start "{window_title}" /wait cmd.exe /c wsl -- bash -c "{bash_script}"'

    status_filename = build_status_name("in_progress", sim_id)
    create_status(sim_dir, base_dir, "in_progress", status_filename)

    print(
        f"[{worker_name}] Janela disparada para simulação #{sim_id}: {sim_dir.name}"
    )

    try:
        # Executa no Windows abrindo o CMD externo visível
        subprocess.run(cmd, shell=True, check=True)
        remove_in_progress(sim_dir, base_dir, status_filename)

        if simulation_ok(sim_dir, log_file):
            create_status(
                sim_dir,
                base_dir,
                "success",
                build_status_name("success", sim_id),
            )
            print(
                f"[{worker_name}] Simulação #{sim_id} concluída com SUCESSO."
            )
        else:
            create_status(
                sim_dir,
                base_dir,
                "error",
                build_status_name("error", sim_id),
            )
            print(
                f"[{worker_name}] Simulação #{sim_id} concluída com ERRO (passos incompletos ou crash)."
            )

    except Exception as err:
        remove_in_progress(sim_dir, base_dir, status_filename)
        create_status(
            sim_dir, base_dir, "error", build_status_name("error", sim_id)
        )
        print(
            f"[{worker_name}] Falha na execução da simulação #{sim_id}: {err}"
        )


# ===============================================================
# 4. WORKER
# ===============================================================
def worker(
    sim_queue: Queue,
    base_dir: Path,
    lmp_bin_wsl: str,
    use_gpu: bool,
    worker_name: str,
):
    while True:
        try:
            sim_id, sim_dir = sim_queue.get_nowait()
        except Empty:
            break

        run_simulation_in_cmd(
            sim_dir=sim_dir,
            base_dir=base_dir,
            lmp_bin_wsl=lmp_bin_wsl,
            sim_id=sim_id,
            use_gpu=use_gpu,
            worker_name=worker_name,
        )

        sim_queue.task_done()


# ===============================================================
# 5. ROTA PRINCIPAL
# ===============================================================
def main(settings):
    base_dir = Path(settings.simulation_folder)

    # Converte o caminho do executável do JSON para o formato nativo do WSL (/home/prh44/...)
    raw_folder = settings.lammps_executable_folder
    folder_wsl = (
        raw_folder.replace("\\\\wsl.localhost\\Ubuntu", "")
        .replace("//wsl.localhost/Ubuntu", "")
        .replace("\\", "/")
    )
    lmp_bin_wsl = f"{folder_wsl}/{settings.lammps_executable_nickname}"

    # Busca todas as subpastas contendo 'density.in'
    all_dirs = [
        p
        for p in base_dir.iterdir()
        if p.is_dir() and (p / "density.in").exists()
    ]

    print(f"\n--- Verificação de Simulações ---")
    print(f"Diretório base: {base_dir}")
    print(f"Executável WSL: {lmp_bin_wsl}")
    print(f"Total de pastas com 'density.in' encontradas: {len(all_dirs)}")

    if not all_dirs:
        print("⚠️ Nenhuma pasta com arquivo 'density.in' foi encontrada.")
        return

    sim_queue = Queue()
    for i, sim_dir in enumerate(all_dirs, start=1):
        sim_queue.put((i, sim_dir))

    threads = [
        Thread(
            target=worker,
            args=(sim_queue, base_dir, lmp_bin_wsl, False, "CPU-1"),
        ),
        Thread(
            target=worker,
            args=(sim_queue, base_dir, lmp_bin_wsl, False, "CPU-2"),
        ),
        Thread(
            target=worker,
            args=(sim_queue, base_dir, lmp_bin_wsl, True, "GPU-1"),
        ),
        Thread(
            target=worker,
            args=(sim_queue, base_dir, lmp_bin_wsl, True, "GPU-2"),
        ),
    ]

    print(f"\nDisparando {len(threads)} workers concorrentes...")

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print("\nTodas as simulações da fila foram processadas.")


if __name__ == "__main__":
    from sternario.settings import load_settings

    settings = load_settings()
    main(settings)