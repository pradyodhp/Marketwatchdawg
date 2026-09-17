"""Replay / simulation screen."""

from frontend.components.replay import render_replay_controls


def render(client, symbols: list[str]) -> None:
    render_replay_controls(client, symbols)
