import math
import re


def dms_str_to_decimal(dms_str):
    """
    解析支持度、分、秒的 DMS 字符串，缺失的分和秒自动补 0。
    示例支持：
    - '22°32′39″N'
    - '22°32′N'
    - '22°N'
    """
    pattern = (
        r"(?P<deg>\d+)[°d]?"  # 度（必选）
        r"\s*(?P<min>\d*)[′\']?"  # 分（可选）
        r'\s*(?P<sec>\d*)[″"]?'  # 秒（可选）
        r"\s*(?P<dir>[NSEW])"  # 方向（必选）
    )
    match = re.match(pattern, dms_str.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid DMS format: {dms_str}")

    deg = int(match.group("deg"))
    min_ = int(match.group("min")) if match.group("min") else 0
    sec = int(match.group("sec")) if match.group("sec") else 0
    direction = match.group("dir").upper()

    decimal = deg + min_ / 60 + sec / 3600
    if direction in ["S", "W"]:
        decimal *= -1
    return decimal


def parse_coord(coord):
    # 如果是字符串，先转为 decimal degrees
    if isinstance(coord, str):
        return dms_str_to_decimal(coord)
    elif isinstance(coord, (int, float)):
        return float(coord)
    else:
        raise TypeError("Coordinate must be a float or DMS string.")


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半径，单位：米
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return R * c  # 米


def light_travel_time(coord1_lat, coord1_lon, coord2_lat, coord2_lon):
    lat1 = parse_coord(coord1_lat)
    lon1 = parse_coord(coord1_lon)
    lat2 = parse_coord(coord2_lat)
    lon2 = parse_coord(coord2_lon)
    distance = haversine(lat1, lon1, lat2, lon2)
    speed_of_light = 299_792_458  # m/s（真空中光速）
    return distance / speed_of_light  # 秒
