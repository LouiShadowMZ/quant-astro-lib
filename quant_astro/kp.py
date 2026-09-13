"""KP 星主、象意星、宫位象意与主宰星计算。"""

from __future__ import annotations

import csv
import os
import re
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


_NUMERIC_COLUMNS = {"From", "To", "Degree", "Min", "Second", "KS-N", "CIL-N", "KS-D", "paada"}


def _default_table_path() -> Path:
    env_path = os.getenv("QUANT_ASTRO_KP_TABLE")
    if env_path:
        return Path(env_path).expanduser().resolve()

    local = Path(__file__).resolve().parent / "data" / "sub-sub.csv"
    if local.exists():
        return local

    package_names = [name for name in (__package__, "quant_astro") if name]
    for package_name in package_names:
        try:
            candidate = Path(str(files(package_name).joinpath("data/sub-sub.csv")))
            if candidate.exists():
                return candidate
        except (ModuleNotFoundError, TypeError):
            continue
    raise FileNotFoundError(
        "找不到 data/sub-sub.csv。请保留原 quant_astro/data 目录，"
        "或设置环境变量 QUANT_ASTRO_KP_TABLE 指向该文件。"
    )


@lru_cache(maxsize=8)
def _load_kp_table_cached(path_text: str) -> tuple[tuple[dict[str, Any], ...], tuple[float, ...]]:
    rows: list[dict[str, Any]] = []
    with Path(path_text).open("r", encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {}
            for key, value in source.items():
                if key in _NUMERIC_COLUMNS and value not in (None, ""):
                    row[key] = float(value)
                else:
                    row[key] = value
            row["From"] = float(row["From"])
            row["To"] = 360.0 if float(row["To"]) == 0.0 else float(row["To"])
            rows.append(row)
    if not rows:
        raise ValueError(f"KP 查找表为空：{path_text}")
    rows.sort(key=lambda item: item["From"])
    return tuple(rows), tuple(float(item["From"]) for item in rows)


def load_kp_table(table_path: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    """加载并缓存 KP 表。默认读取包内 ``data/sub-sub.csv``。"""
    path = Path(table_path).expanduser().resolve() if table_path else _default_table_path()
    # 不暴露缓存中的可变 dict，避免调用方修改一行后污染进程内所有后续查询。
    return tuple(dict(row) for row in _load_kp_table_cached(str(path))[0])


def _table_with_starts(table_path: str | Path | None = None) -> tuple[tuple[dict[str, Any], ...], tuple[float, ...]]:
    path = Path(table_path).expanduser().resolve() if table_path else _default_table_path()
    return _load_kp_table_cached(str(path))


def kp_lookup(longitude: float, *, table_path: str | Path | None = None) -> dict[str, Any]:
    """以单个黄经查询 Sign/Star/Sub/Sub-Sub、Paada 及各级星主。"""
    lon = float(longitude) % 360.0
    rows, starts = _table_with_starts(table_path)
    index = bisect_right(starts, lon) - 1
    if index < 0:
        index = len(rows) - 1
    row = rows[index]
    if not (float(row["From"]) <= lon < float(row["To"])):
        # 防御非连续或未排序的外部表。
        row = next(
            (candidate for candidate in rows if float(candidate["From"]) <= lon < float(candidate["To"])),
            None,
        )
        if row is None:
            raise LookupError(f"KP 表中没有覆盖黄经 {lon}° 的区间。")
    return {
        "sign": row["Sign"],
        "star": row["Star"],
        "sign_lord": row["Sign-Lord"],
        "star_lord": row["Star-Lord"],
        "sub_lord": row["Sub-Lord"],
        "sub_sub_lord": row["Sub-Sub-Lord"],
        "sign_degree": lon % 30.0,
        "paada": int(float(row["paada"])),
    }


def kp_lookup_many(
    values: Mapping[str, float | Mapping[str, Any]] | Iterable[float],
    *,
    table_path: str | Path | None = None,
) -> dict[str, dict[str, Any]] | list[dict[str, Any]]:
    """批量 KP 查询；字典值既可为黄经，也可为含 ``lon`` 的坐标字典。"""
    if isinstance(values, Mapping):
        output: dict[str, dict[str, Any]] = {}
        for name, value in values.items():
            longitude = value["lon"] if isinstance(value, Mapping) else value
            output[str(name)] = kp_lookup(float(longitude), table_path=table_path)
        return output
    return [kp_lookup(float(value), table_path=table_path) for value in values]


def get_horary_ascendant(
    number: int,
    *,
    mode: str = "KS-N",
    table_path: str | Path | None = None,
) -> float:
    """将 1–249（KS-N）或 1–2193（CIL-N）签号转换为目标上升黄经。"""
    normalized_mode = mode.strip().upper()
    if normalized_mode in {"KS-N", "249"}:
        number_column, result_column, lower, upper = "KS-N", "KS-D", 1, 249
    elif normalized_mode in {"CIL-N", "2193", "1-2193"}:
        number_column, result_column, lower, upper = "CIL-N", "From", 1, 2193
    else:
        raise ValueError("mode 只能是 'KS-N'（249）或 'CIL-N'/'1-2193'（2193）。")
    try:
        target_number = int(number)
    except (TypeError, ValueError) as exc:
        raise ValueError("卜卦签号必须是整数。") from exc
    if target_number != float(number) or not lower <= target_number <= upper:
        raise ValueError(f"{normalized_mode} 签号必须是 {lower}–{upper} 的整数。")

    for row in load_kp_table(table_path):
        if int(float(row[number_column])) == target_number:
            return float(row[result_column]) % 360.0
    raise LookupError(f"KP 表中找不到 {normalized_mode} 签号 {target_number}。")


def _unwrap_house_positions(
    house_data: Mapping[str, Any],
) -> Mapping[str, Mapping[str, Any]]:
    """同时接受 calculate_houses 的完整结果或旧式纯宫头字典。"""
    nested = house_data.get("houses")
    if isinstance(nested, Mapping):
        return nested
    return house_data


def get_kp_lords(
    planet_dict: Mapping[str, Mapping[str, Any]],
    house_dict: Mapping[str, Any],
    *,
    table_path: str | Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """分别批量查询行星和宫头；可直接传入完整宫位求解结果。"""
    return (
        kp_lookup_many(planet_dict, table_path=table_path),
        kp_lookup_many(_unwrap_house_positions(house_dict), table_path=table_path),
    )


def _house_number(key: str) -> int:
    match = re.search(r"(\d+)$", str(key).strip())
    if not match:
        raise ValueError(f"无法从宫位键 {key!r} 提取宫号。")
    number = int(match.group(1))
    if not 1 <= number <= 12:
        raise ValueError(f"宫号超出 1–12：{number}")
    return number


def _house_for_longitude(longitude: float, cusps: Mapping[int, float]) -> int:
    lon = float(longitude) % 360.0
    for number in range(1, 13):
        start = cusps[number] % 360.0
        end = cusps[1 if number == 12 else number + 1] % 360.0
        if start < end and start <= lon < end:
            return number
        if start >= end and (lon >= start or lon < end):
            return number
    raise RuntimeError(f"无法判断黄经 {lon}° 的落宫。")


def _deduplicate(values: Iterable[Any]) -> list[Any]:
    return list(dict.fromkeys(value for value in values if value is not None))


def _kp_houses_by_number(
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
) -> dict[int, Mapping[str, Any]]:
    return {
        _house_number(key): value
        for key, value in kp_house_results.items()
        if value is not None
    }


@dataclass(frozen=True)
class SignificatorMaps:
    """ABCD 与 1234 共用的中间映射，可在局部刷新时复用。"""

    planet_order: tuple[str, ...]
    occupancy: Mapping[str, int]
    ownership: Mapping[str, tuple[int, ...]]
    star_lords: Mapping[str, str]
    house_occupants: Mapping[int, tuple[str, ...]]


def build_significator_maps(
    planet_pos: Mapping[str, Mapping[str, Any]],
    house_pos: Mapping[str, Any],
    kp_planet_results: Mapping[str, Mapping[str, Any] | None],
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
) -> SignificatorMaps:
    """一次建立两类象意计算共用的落宫、守护与宿主映射。"""
    cusp_positions = _unwrap_house_positions(house_pos)
    cusps = {_house_number(key): float(value["lon"]) for key, value in cusp_positions.items()}
    missing = set(range(1, 13)) - set(cusps)
    if missing:
        raise ValueError(f"宫位数据不完整，缺少：{sorted(missing)}")

    occupancy = {
        name: _house_for_longitude(float(position["lon"]), cusps)
        for name, position in planet_pos.items()
    }
    ownership_lists: defaultdict[str, list[int]] = defaultdict(list)
    for key, kp_data in kp_house_results.items():
        if kp_data:
            ownership_lists[str(kp_data["sign_lord"])].append(_house_number(key))
    ownership = {name: tuple(sorted(set(houses))) for name, houses in ownership_lists.items()}
    star_lords = {
        name: str(kp_data["star_lord"])
        for name, kp_data in kp_planet_results.items()
        if kp_data and kp_data.get("star_lord")
    }
    house_occupants_lists: defaultdict[int, list[str]] = defaultdict(list)
    for planet, house in occupancy.items():
        house_occupants_lists[house].append(planet)
    house_occupants = {
        number: tuple(house_occupants_lists.get(number, ()))
        for number in range(1, 13)
    }
    return SignificatorMaps(
        planet_order=tuple(planet_pos),
        occupancy=MappingProxyType(occupancy),
        ownership=MappingProxyType(ownership),
        star_lords=MappingProxyType(star_lords),
        house_occupants=MappingProxyType(house_occupants),
    )


def calculate_planet_significators(
    planet_pos: Mapping[str, Mapping[str, Any]],
    house_pos: Mapping[str, Any],
    kp_planet_results: Mapping[str, Mapping[str, Any] | None],
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
    *,
    shared_maps: SignificatorMaps | None = None,
) -> dict[str, dict[str, list[int]]]:
    """独立计算行星 ABCD 象意宫位。传入 ``shared_maps`` 可免除重复映射。"""
    maps = shared_maps or build_significator_maps(
        planet_pos, house_pos, kp_planet_results, kp_house_results
    )
    output: dict[str, dict[str, list[int]]] = {}
    for planet in maps.planet_order:
        star_lord = maps.star_lords.get(planet)
        output[planet] = {
            "A": _deduplicate([maps.occupancy.get(star_lord)] if star_lord else []),
            "B": _deduplicate([maps.occupancy.get(planet)]),
            "C": list(maps.ownership.get(star_lord, ())) if star_lord else [],
            "D": list(maps.ownership.get(planet, ())),
        }
    return output


def calculate_house_significators(
    planet_pos: Mapping[str, Mapping[str, Any]],
    house_pos: Mapping[str, Any],
    kp_planet_results: Mapping[str, Mapping[str, Any] | None],
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
    *,
    shared_maps: SignificatorMaps | None = None,
) -> dict[int, dict[str, list[str]]]:
    """独立计算 12 宫的 1234 级象意星。传入 ``shared_maps`` 可免除重复映射。"""
    maps = shared_maps or build_significator_maps(
        planet_pos, house_pos, kp_planet_results, kp_house_results
    )
    output: dict[int, dict[str, list[str]]] = {}
    kp_houses = _kp_houses_by_number(kp_house_results)
    for house_number in range(1, 13):
        kp_data = kp_houses.get(house_number)
        lord = str(kp_data["sign_lord"]) if kp_data else None
        occupants = list(maps.house_occupants[house_number])
        level_1 = [
            planet
            for occupant in occupants
            for planet, star_lord in maps.star_lords.items()
            if star_lord == occupant
        ]
        level_3 = [
            planet
            for planet, star_lord in maps.star_lords.items()
            if lord is not None and star_lord == lord
        ]
        output[house_number] = {
            "1": _deduplicate(level_1),
            "2": _deduplicate(occupants),
            "3": _deduplicate(level_3),
            "4": [lord] if lord else [],
        }
    return output


def calculate_significators(
    planet_pos: Mapping[str, Mapping[str, Any]],
    house_pos: Mapping[str, Any],
    kp_planet_results: Mapping[str, Mapping[str, Any] | None],
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
) -> tuple[dict[str, dict[str, list[int]]], dict[int, dict[str, list[str]]]]:
    """同时需要 ABCD 与 1234 时只建立一次共享映射。"""
    maps = build_significator_maps(planet_pos, house_pos, kp_planet_results, kp_house_results)
    return (
        calculate_planet_significators(
            planet_pos,
            house_pos,
            kp_planet_results,
            kp_house_results,
            shared_maps=maps,
        ),
        calculate_house_significators(
            planet_pos,
            house_pos,
            kp_planet_results,
            kp_house_results,
            shared_maps=maps,
        ),
    )


def get_ruling_planets(
    kp_planet_results: Mapping[str, Mapping[str, Any] | None],
    kp_house_results: Mapping[str, Mapping[str, Any] | None],
    day_lord: str | Mapping[str, Any] | None = None,
    *,
    asc_kp_result: Mapping[str, Any] | None = None,
) -> dict[str, str | None]:
    """提取真实 Asc、Moon 的 Sign/Star/Sub Lord，并按需加入值日星。

    ``asc_kp_result`` 应由四轴中的真实 ``axes['Asc']['lon']`` 查询得到。
    未传时为兼容旧调用才回退到第一宫宫头；Whole Sign、Vehlow、Equal/Zodiac
    等宫位制下第一宫宫头并不等于真实 Asc，新的调用代码始终显式传入该参数。
    """
    asc = asc_kp_result or _kp_houses_by_number(kp_house_results).get(1, {})
    moon = kp_planet_results.get("Mo") or {}
    result: dict[str, str | None] = {
        "Asc_Sign_Lord": asc.get("sign_lord"),
        "Asc_Star_Lord": asc.get("star_lord"),
        "Asc_Sub_Lord": asc.get("sub_lord"),
        "Moon_Sign_Lord": moon.get("sign_lord"),
        "Moon_Star_Lord": moon.get("star_lord"),
        "Moon_Sub_Lord": moon.get("sub_lord"),
    }
    if isinstance(day_lord, Mapping):
        day_lord = day_lord.get("day_lord")
    if day_lord:
        result["Day_Lord"] = str(day_lord)
    return result


# 旧调用名保留为轻量别名，便于渐进迁移。
get_significators = calculate_significators
