import numpy as np


def calculate_b2_points(
    b2,
    reduction_factor,
    minimum_step
):
    """
    Gera pontos de amostragem em NumPy partindo de 0 até b2_safe com incremento
    de minimum_step, garantindo que b2_safe esteja SEMPRE incluído no final.
    """
    b2_safe = b2 * reduction_factor

    if b2_safe <= 0:
        raise ValueError('molalidade calculada negativa')

    # Determina o número exato de passos sem ultrapassar b2_safe
    num_steps = int(np.floor(b2_safe / minimum_step)) + 1

    # Cria a sequência de passos regulares
    points = np.arange(num_steps) * minimum_step

    # Se o último ponto não for exatamente o b2_safe, adiciona b2_safe no final
    if not np.isclose(points[-1], b2_safe):
        points = np.append(points, b2_safe)

    return points


if __name__ == "__main__":
    print("\nTEST")
    result = calculate_b2_points(0.04, minimum_step=0.05)
    print("RESULT:", result)
    print("MAX VALUE:", result.max())
