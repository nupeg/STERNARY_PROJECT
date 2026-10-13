
from pathlib import Path

import numpy as np
import pandas as pd

from sternario.settings import load_settings


# ==========================================================
# MOLECULE-TO-ATOM-TYPE MAPPING
# ==========================================================

MAPA_ATOM_TYPES = {
    "H2O": ["OW", "HW"],
    "SO4": ["S", "OS"],
    "F": ["F"],
    "Cl": ["Cl"],
    "Br": ["Br"],
    "I": ["I"],
    "Li": ["Li"],
    "Na": ["Na"],
    "K": ["K"],
    "Rb": ["Rb"],
    "Cs": ["Cs"],
    "Mg": ["Mg"],
    "Ca": ["Ca"],
}


class LammpsCoefficientsProcessor:
    """Identify atom types and generate LAMMPS force-field coefficients."""

    def __init__(self, settings=None):
        self.settings = settings or load_settings()

        # Centralized paths from settings.json
        self.simulation_folder = Path(self.settings.simulation_folder)
        self.lammps_script_folder = Path(
            self.settings.lammps_script_folder
        )

        self.setup_playmol_file = self.settings.setup_playmol_file
        self.playmol_log_file = self.settings.playmol_log_file

        self.sigma_file = (
            self.lammps_script_folder / self.settings.sig_file
        )
        self.epsilon_file = (
            self.lammps_script_folder / self.settings.eps_file
        )

        self.sigma_table = None
        self.epsilon_table = None

    # ------------------------------------------------------
    # LOAD LENNARD-JONES TABLES
    # ------------------------------------------------------

    def carregar_tabelas(self):
        """Load sigma and epsilon tables from the configured directory."""

        if not self.sigma_file.is_file():
            raise FileNotFoundError(
                f"Sigma table not found: {self.sigma_file}"
            )

        if not self.epsilon_file.is_file():
            raise FileNotFoundError(
                f"Epsilon table not found: {self.epsilon_file}"
            )

        self.sigma_table = pd.read_excel(
            self.sigma_file,
            index_col=0
        )

        self.epsilon_table = pd.read_excel(
            self.epsilon_file,
            index_col=0
        )

        return self.sigma_table, self.epsilon_table

    # ------------------------------------------------------
    # IDENTIFY ATOM TYPES IN A SIMULATION
    # ------------------------------------------------------

    def identificar_atom_types(self, simulation):
        """
        Identify atom types using setup.playmol first,
        then playmol.log if the setup file does not exist.
        """

        setup_path = simulation / self.setup_playmol_file
        log_path = simulation / self.playmol_log_file

        if setup_path.is_file():
            source_file = setup_path
        elif log_path.is_file():
            source_file = log_path
        else:
            print(
                f"[WARNING] Neither {self.setup_playmol_file} nor "
                f"{self.playmol_log_file} was found in {simulation}"
            )
            return []

        detected_molecules = []

        with source_file.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if line.startswith("include") and ".mol" in line:
                    parts = line.split()

                    if len(parts) < 2:
                        continue

                    molecule = Path(parts[1]).stem
                    detected_molecules.append(molecule)

        atom_types = []

        for molecule in detected_molecules:
            if molecule in MAPA_ATOM_TYPES:
                atom_types.extend(MAPA_ATOM_TYPES[molecule])
            else:
                print(
                    f"[WARNING] Molecule not mapped: {molecule} "
                    f"(folder: {simulation.name})"
                )

        # Remove duplicates while preserving their original order
        unique_atom_types = []
        seen_atom_types = set()

        for atom in atom_types:
            if atom not in seen_atom_types:
                seen_atom_types.add(atom)
                unique_atom_types.append(atom)

        return unique_atom_types

    # ------------------------------------------------------
    # LOOK UP TABLE VALUE, INCLUDING SYMMETRIC POSITION
    # ------------------------------------------------------

    @staticmethod
    def buscar_valor_tabela(table, atom_a, atom_b):
        """Look up a value, checking the symmetric cell if needed."""

        try:
            value = table.loc[atom_a, atom_b]
        except KeyError as error:
            raise KeyError(
                f"Atom pair '{atom_a}', '{atom_b}' is missing "
                "from the Lennard-Jones table."
            ) from error

        # If the cell is empty, try the symmetric position
        if pd.isna(value):
            try:
                symmetric_value = table.loc[atom_b, atom_a]
            except KeyError as error:
                raise KeyError(
                    f"Symmetric atom pair '{atom_b}', '{atom_a}' "
                    "is missing from the Lennard-Jones table."
                ) from error

            if not pd.isna(symmetric_value):
                return symmetric_value

        return value

    # ------------------------------------------------------
    # OBTAIN LENNARD-JONES PARAMETERS
    # ------------------------------------------------------

    def obter_parametros_lj(
        self,
        atom_a,
        atom_b,
        sigma_table=None,
        epsilon_table=None
    ):
        """Return epsilon and sigma, preserving the original rules."""

        sigma_table = sigma_table if sigma_table is not None else self.sigma_table
        epsilon_table = (
            epsilon_table
            if epsilon_table is not None
            else self.epsilon_table
        )

        if sigma_table is None or epsilon_table is None:
            raise RuntimeError(
                "Load the Lennard-Jones tables before calculating parameters."
            )

        # Interactions involving hydrogen are set to zero
        if atom_a.startswith("H") or atom_b.startswith("H"):
            return 0.0, 0.0

        sigma = self.buscar_valor_tabela(
            sigma_table,
            atom_a,
            atom_b
        )
        epsilon = self.buscar_valor_tabela(
            epsilon_table,
            atom_a,
            atom_b
        )

        # Apply Lorentz-Berthelot combining rules when explicitly requested
        if (
            isinstance(sigma, str) and sigma.strip().upper() == "LB"
        ) or (
            isinstance(epsilon, str) and epsilon.strip().upper() == "LB"
        ):
            sigma_a = float(sigma_table.loc[atom_a, atom_a])
            sigma_b = float(sigma_table.loc[atom_b, atom_b])

            epsilon_a = float(epsilon_table.loc[atom_a, atom_a])
            epsilon_b = float(epsilon_table.loc[atom_b, atom_b])

            sigma_lb = (sigma_a + sigma_b) / 2
            epsilon_lb = np.sqrt(epsilon_a * epsilon_b)

            return float(epsilon_lb), float(sigma_lb)

        # Return explicitly specified values
        return float(epsilon), float(sigma)

    # ------------------------------------------------------
    # GENERATE coeffs.lmp
    # ------------------------------------------------------

    def gerar_coeffs_lammps(
        self,
        simulation,
        atom_types,
        sigma_table=None,
        epsilon_table=None
    ):
        """Generate coeffs.lmp in the simulation directory."""

        sigma_table = sigma_table if sigma_table is not None else self.sigma_table
        epsilon_table = (
            epsilon_table
            if epsilon_table is not None
            else self.epsilon_table
        )

        output_path = simulation / "coeffs.lmp"

        with output_path.open("w", encoding="utf-8") as file:
            file.write("# PAIR COEFFS lj_madrid2019 STYLE\n")

            # Write all pair interactions using the detected atom-type order
            for i, atom_a in enumerate(atom_types):
                for j, atom_b in enumerate(atom_types):
                    epsilon, sigma = self.obter_parametros_lj(
                        atom_a,
                        atom_b,
                        sigma_table,
                        epsilon_table
                    )

                    file.write(
                        f"pair_coeff {i + 1} {j + 1} "
                        f"{epsilon:.4f} {sigma:.4f} "
                        f"# {atom_a} {atom_b}\n"
                    )

            # Bond coefficients
            file.write("\n# BOND COEFFS\n")
            file.write("bond_coeff 1 235.00 0.9572    # HW OW\n")

            if "S" in atom_types and "OS" in atom_types:
                file.write(
                    "bond_coeff 2 525.150 1.487    # S OS\n"
                )

            # Angle coefficients
            file.write("\n# ANGLE COEFFS\n")
            file.write("angle_coeff 1 100.00 104.52    # HW OW\n")

            if "S" in atom_types and "OS" in atom_types:
                file.write(
                    "angle_coeff 2 139.920 109.470  # OS S\n"
                )

        print(f"[OK] File created: {output_path}")
        return output_path

    # ------------------------------------------------------
    # PROCESS ALL SIMULATION FOLDERS
    # ------------------------------------------------------

    def execute(self):
        """Generate LAMMPS coefficients for simulation subdirectories."""

        if not self.simulation_folder.is_dir():
            raise NotADirectoryError(
                f"Simulation directory not found: {self.simulation_folder}"
            )

        # Load tables once for all simulations
        sigma_table, epsilon_table = self.carregar_tabelas()

        simulations = sorted(
            folder
            for folder in self.simulation_folder.iterdir()
            if folder.is_dir() and folder.name.lower() != "logs"
        )

        total_generated = 0
        total_without_atom_types = 0
        total_failed = 0

        print(f"Simulation directory: {self.simulation_folder}")
        print(f"Simulation folders found: {len(simulations)}")

        for simulation in simulations:
            print(f"\nProcessing: {simulation.name}")

            try:
                atom_types = self.identificar_atom_types(simulation)

                if not atom_types:
                    total_without_atom_types += 1
                    continue

                print(f"Atom types: {atom_types}")

                self.gerar_coeffs_lammps(
                    simulation,
                    atom_types,
                    sigma_table,
                    epsilon_table
                )

                total_generated += 1

            except Exception as error:
                total_failed += 1
                print(
                    f"[ERROR] Failed to generate coefficients for "
                    f"{simulation.name}: {error}"
                )

        print("\n" + "=" * 50)
        print("LAMMPS COEFFICIENTS SUMMARY")
        print("=" * 50)
        print(f"Simulation folders found: {len(simulations)}")
        print(f"Files generated: {total_generated}")
        print(f"Folders without atom types: {total_without_atom_types}")
        print(f"Failed folders: {total_failed}")
        print("=" * 50)


def main():
    """Run the LAMMPS coefficient-generation routine."""

    processor = LammpsCoefficientsProcessor()
    processor.execute()


if __name__ == "__main__":
    main()