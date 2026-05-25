from __future__ import annotations

from datetime import date, timedelta
import re
from typing import Any, Iterable

from mealie_planner.selection.schema import RecipeCandidate, WeatherContext


QUICK_TAGS = {"30 Minutes", "45 Minutes", "Fresh", "Outdoor Friendly", "Summer"}
COZY_TAGS = {"Cozy", "Soup / Stew", "Casserole / Bake", "60 Minutes", "Time Intensive"}


def choose_plan_dates(
    *,
    start_date: date,
    day_count: int,
    dinner_count: int,
    blocked_dates: set[date] | None = None,
) -> list[date]:
    blocked = blocked_dates or set()
    days: list[date] = []
    for offset in range(day_count):
        candidate = start_date + timedelta(days=offset)
        if candidate in blocked:
            continue
        days.append(candidate)
        if len(days) >= dinner_count:
            break
    return days


def prefilter_recipes(
    recipes: Iterable[RecipeCandidate],
    *,
    guidance: str,
    weather: WeatherContext,
    max_candidates: int = 40,
) -> list[RecipeCandidate]:
    guidance_terms = set(re.findall(r"[a-z0-9]+", guidance.lower()))
    hot_week = any((day.get("high_f") or day.get("temperature") or 0) >= 78 for day in weather.daily)

    scored: list[tuple[int, str, RecipeCandidate]] = []
    for item in recipes:
        score = 0
        haystack = " ".join(
            [item.slug, item.title, *item.categories, *item.tags, *item.tools, *item.ingredient_anchors]
        ).lower()
        if "dinner" in {category.lower() for category in item.categories}:
            score += 20
        else:
            score -= 20
        if guidance_terms:
            score += sum(5 for term in guidance_terms if term in haystack)
        tag_set = set(item.tags)
        if hot_week:
            score += 4 * len(tag_set & QUICK_TAGS)
            score -= 2 * len(tag_set & COZY_TAGS)
        else:
            score += 2 * len(tag_set & COZY_TAGS)
        scored.append((score, item.title.lower(), item))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in scored[:max_candidates]]


def build_compact_context(candidates: Iterable[RecipeCandidate]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "slug": item.slug,
            "title": item.title,
            "categories": item.categories,
            "tags": item.tags,
            "tools": item.tools,
            "servings": item.servings,
            "ingredient_anchors": item.ingredient_anchors[:10],
        }
        for item in candidates
    ]

