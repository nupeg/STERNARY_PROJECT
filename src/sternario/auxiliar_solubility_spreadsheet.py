import numpy as np


def calculate_b2_points(
    b2,
    reduction_factor,
    minimum_step
):
    """
    Gera pontos de amostragem em NumPy partindo de 0 até b2_safe com incremento
    de minimum_step, garantindo que b2_safe nunca seja ultrapassado.
    """
    b2_safe = b2 * reduction_factor

    if b2_safe <= 0:
        raise ValueError(f'molalidade calculada negativa')

    # Determina o número exato de passos sem ultrapassar b2_safe
    num_steps = int(np.floor(b2_safe / minimum_step)) + 1

    if num_steps <= 1:
        return np.array([b2_safe])
    
    # Cria o array e aplica o arredondamento para limpar ruídos flutuantes
    points = np.arange(num_steps) * minimum_step

    return points


if __name__ == "__main__":
    print("\nTEST")
    result = calculate_b2_points(0.04, minimum_step=0.05)
    print("RESULT:", result)
    print("MAX VALUE:", result.max())
