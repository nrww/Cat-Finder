# utils.py
import numpy as np
import scipy.interpolate

def catmull_rom_spline(points, num_points=100):
    """
    Генерирует кривую Кэтмулл-Рома по заданным опорным точкам.
    
    Parameters:
        points (list of tuples): Список опорных точек (x, y).
        num_points (int): Количество интерполированных точек.
    
    Returns:
        numpy.ndarray: Интерполированные точки кривой.
    """
    points = np.array(points)
    x = points[:, 0]
    y = points[:, 1]

    # Параметр t для интерполяции
    t = np.linspace(0, 1, len(points))
    spline_x = scipy.interpolate.CubicSpline(t, x, bc_type='natural')
    spline_y = scipy.interpolate.CubicSpline(t, y, bc_type='natural')

    t_new = np.linspace(0, 1, num_points)
    x_new = spline_x(t_new)
    y_new = spline_y(t_new)

    return np.stack((x_new, y_new), axis=1).astype(np.int32)
