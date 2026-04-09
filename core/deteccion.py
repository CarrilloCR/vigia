"""
Anomaly detection methods for KPI monitoring.

Three approaches combined via ensemble:
1. Statistical — mean + threshold deviation (original method)
2. Prophet — time-series forecasting with confidence intervals
3. PyOD (Isolation Forest) — unsupervised outlier detection
"""

import logging
import statistics

logger = logging.getLogger(__name__)


def detectar_estadistico(valor_actual, historico, umbral=20):
    """
    Statistical detection based on mean deviation.
    Returns: (is_anomaly, expected_value, deviation_percent)
    """
    if len(historico) < 5:
        return False, 0, 0
    promedio = statistics.mean(historico)
    if promedio == 0:
        return False, 0, 0
    desviacion = abs((valor_actual - promedio) / promedio) * 100
    es_anomalia = desviacion >= umbral
    return es_anomalia, round(promedio, 2), round(desviacion, 2)


def detectar_prophet(valor_actual, historico_con_fechas):
    """
    Prophet time-series forecasting.
    historico_con_fechas: list of (datetime, value) tuples, ordered chronologically.
    Returns: (is_anomaly, expected_value, deviation_percent) or (None, None, None) on failure.
    """
    try:
        import pandas as pd
        from prophet import Prophet
    except ImportError:
        logger.warning("Prophet no instalado, omitiendo deteccion Prophet")
        return None, None, None

    if len(historico_con_fechas) < 14:
        return None, None, None

    try:
        # Suppress Prophet/cmdstanpy verbose output
        logging.getLogger('prophet').setLevel(logging.WARNING)
        logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

        df = pd.DataFrame(historico_con_fechas, columns=['ds', 'y'])
        df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)

        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05,
            interval_width=0.90,
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=1, freq='D')
        forecast = model.predict(future)

        last_row = forecast.iloc[-1]
        yhat = last_row['yhat']
        yhat_lower = last_row['yhat_lower']
        yhat_upper = last_row['yhat_upper']

        es_anomalia = valor_actual < yhat_lower or valor_actual > yhat_upper

        if yhat == 0:
            desviacion = 0.0
        else:
            desviacion = abs((valor_actual - yhat) / yhat) * 100

        return es_anomalia, round(float(yhat), 2), round(desviacion, 2)

    except Exception as e:
        logger.error(f"Error en deteccion Prophet: {e}")
        return None, None, None


def detectar_pyod(valor_actual, historico, contamination=0.1):
    """
    PyOD Isolation Forest outlier detection.
    Returns: (is_anomaly, expected_value, deviation_percent) or (None, None, None) on failure.
    """
    try:
        import numpy as np
        from pyod.models.iforest import IForest
    except ImportError:
        logger.warning("PyOD no instalado, omitiendo deteccion PyOD")
        return None, None, None

    if len(historico) < 10:
        return None, None, None

    try:
        X_train = np.array(historico).reshape(-1, 1)
        X_test = np.array([[valor_actual]])

        clf = IForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        clf.fit(X_train)

        prediccion = clf.predict(X_test)[0]

        promedio = float(np.mean(X_train))
        if promedio == 0:
            desviacion = 0.0
        else:
            desviacion = abs((valor_actual - promedio) / promedio) * 100

        es_anomalia = prediccion == 1
        return es_anomalia, round(promedio, 2), round(desviacion, 2)

    except Exception as e:
        logger.error(f"Error en deteccion PyOD: {e}")
        return None, None, None


def detectar_anomalia_ensemble(valor_actual, historico, historico_con_fechas=None, umbral=20):
    """
    Ensemble anomaly detection: combines statistical, Prophet, and PyOD.
    Uses majority vote when multiple methods are available.

    Returns: (is_anomaly, expected_value, deviation_percent, method_name)
    """
    resultados = {}

    # 1. Statistical (always runs)
    stat_anom, stat_esp, stat_dev = detectar_estadistico(valor_actual, historico, umbral)
    resultados['estadistico'] = (stat_anom, stat_esp, stat_dev)

    # 2. Prophet (needs 14+ data points with dates)
    if historico_con_fechas and len(historico_con_fechas) >= 14:
        prophet_res = detectar_prophet(valor_actual, historico_con_fechas)
        if prophet_res[0] is not None:
            resultados['prophet'] = prophet_res

    # 3. PyOD (needs 10+ data points)
    if len(historico) >= 10:
        pyod_res = detectar_pyod(valor_actual, historico)
        if pyod_res[0] is not None:
            resultados['pyod'] = pyod_res

    # Single method fallback
    if len(resultados) == 1:
        return stat_anom, stat_esp, stat_dev, 'estadistico'

    # Majority vote
    votos = sum(1 for r in resultados.values() if r[0])
    total_metodos = len(resultados)
    es_anomalia = votos > total_metodos / 2

    # Use Prophet's expected value when available (trend-aware), else statistical
    if 'prophet' in resultados and resultados['prophet'][1] is not None:
        valor_esperado = resultados['prophet'][1]
        desviacion = resultados['prophet'][2]
    else:
        valor_esperado = stat_esp
        desviacion = stat_dev

    # Build method label
    metodos_que_flaggearon = sorted(name for name, r in resultados.items() if r[0])
    if es_anomalia and metodos_que_flaggearon:
        metodo = 'ensemble:' + '+'.join(metodos_que_flaggearon)
    elif not es_anomalia:
        metodo = 'ensemble:sin_anomalia'
    else:
        metodo = 'estadistico'

    return es_anomalia, valor_esperado, desviacion, metodo
