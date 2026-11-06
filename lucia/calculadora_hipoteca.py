def calcular_hipoteca(
    precio_vivienda,
    entrada,
    tipo_interes_anual,
    años,
):
    if precio_vivienda <= 0:
        raise ValueError("El precio de la vivienda debe ser positivo.")

    if entrada < 0 or entrada >= precio_vivienda:
        raise ValueError(
            "La entrada debe ser igual o superior a cero "
            "e inferior al precio de la vivienda."
        )

    if tipo_interes_anual < 0:
        raise ValueError("El tipo de interés no puede ser negativo.")

    if años <= 0:
        raise ValueError("El plazo debe ser positivo.")

    importe_prestamo = precio_vivienda - entrada
    interes_mensual = tipo_interes_anual / 100 / 12
    numero_cuotas = años * 12

    if interes_mensual == 0:
        cuota_mensual = importe_prestamo / numero_cuotas
    else:
        cuota_mensual = (
            importe_prestamo
            * interes_mensual
            * (1 + interes_mensual) ** numero_cuotas
            / ((1 + interes_mensual) ** numero_cuotas - 1)
        )

    importe_total = cuota_mensual * numero_cuotas
    intereses_totales = importe_total - importe_prestamo

    return {
        "importe_prestamo": importe_prestamo,
        "cuota_mensual": cuota_mensual,
        "tipo_interes_anual": tipo_interes_anual,
        "años": años,
        "importe_total": importe_total,
        "intereses_totales": intereses_totales,
    }