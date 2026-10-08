"""Fuzz the SPA: every route and malformed path must render without uncaught page errors."""

from __future__ import annotations

import time

import pytest

ROUTES = [
    "/", "/workspace/inbox", "/workspace/pulse", "/workspace/my-issues/assigned",
    "/workspace/initiatives", "/workspace/projects", "/workspace/views",
    "/workspace/team/eng/home", "/workspace/team/eng/active", "/workspace/team/eng/cycles",
    "/workspace/team/eng/projects/all", "/workspace/team/eng/views/issues",
    "/workspace/team/eng/cycle/active", "/workspace/team/eng/cycle/upcoming",
    "/workspace/team/eng/cycles/settings", "/workspace/settings", "/workspace/members",
    "/workspace/issue/NOPE-999/x", "/workspace/project/does-not-exist",
    "/workspace/cycle/does-not-exist", "/workspace/team/missing/home",
    "/workspace/team/eng/", "/workspace/team//home", "/workspace/%E0%A4%A",
    "/workspace/team/eng/home?x=<script>alert(1)</script>", "/nope/nothing/here",
]


@pytest.mark.parametrize("path", ROUTES)
def test_route_renders_without_uncaught_errors(browser_pair, path):
    from playwright.sync_api import sync_playwright  # noqa: F401  (browser_pair owns lifecycle)

    base, (page, _) = browser_pair
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)[:200]))
    page.goto(base + "/")
    page.wait_for_load_state("networkidle")
    page.goto(base + path)
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)
    assert page.locator("body").count() == 1
    assert not errors, errors
