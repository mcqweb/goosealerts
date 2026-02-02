#!/usr/bin/env python3
"""Unit tests for wait_for_lineups behavior"""

from virgin_goose import destination_allows_lineups


def test_destination_allows_lineups_true_default():
    dest = {}
    assert destination_allows_lineups(dest, confirmed_starters_available=True, player_confirmed=True) is True
    assert destination_allows_lineups(dest, confirmed_starters_available=False, player_confirmed=False) is False


def test_destination_with_flag_false_allows():
    dest = {'wait_for_lineups': False}
    assert destination_allows_lineups(dest, confirmed_starters_available=False, player_confirmed=False) is True
    assert destination_allows_lineups(dest, confirmed_starters_available=True, player_confirmed=True) is True


def test_destination_with_flag_true_requires_both():
    dest = {'wait_for_lineups': True}
    assert destination_allows_lineups(dest, confirmed_starters_available=True, player_confirmed=True) is True
    assert destination_allows_lineups(dest, confirmed_starters_available=True, player_confirmed=False) is False
    assert destination_allows_lineups(dest, confirmed_starters_available=False, player_confirmed=True) is False
