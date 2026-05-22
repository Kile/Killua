"""Per-spell ``cards use`` integration tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from ...static.constants import FREE_SLOTS
from ...utils.classes import User
from ...utils.classes.card import Card
from ..harnesses import (
    ATTACK_TIMEOUT_FRAGMENT,
    DEFAULT_ATTACK_SPELL,
    MET_ERROR_FRAGMENT,
    STEAL_TARGET_CARD,
    assert_content_contains,
    assert_embed_title,
    assert_inventory,
    assert_met_error,
    assert_steal_blocked_by_defense,
    assert_steal_succeeded,
    embed_at,
    ensure_no_defense,
    invoke_use,
    last_content,
    patch_random_choice,
    reload_user,
    respond_defense_with_spell,
    respond_to_view,
    run_attack_against_defender,
    seed_channel_history,
    setup_author_spell,
    setup_met_view_spell,
    setup_target_user,
    target_member,
    use_view_spell_paginator,
)
from ..testing import Testing, test
from .cards import TestingUseSpell


class UseSpell1001(TestingUseSpell):
    @test
    async def success_starts_paginator(self) -> None:
        target, tid = await setup_met_view_spell(self, 1001, 50_001, fs_cards=[1011, 1010])
        await use_view_spell_paginator(self, 1001, target)

    @test
    async def not_met(self) -> None:
        target, _ = target_member(self, 50_002)
        await setup_author_spell(self.base_author.id, 1001)
        await setup_target_user(target.id, fs_cards=[1011])
        await invoke_use(self, 1001, target=target)
        assert_met_error(self.base_context)

    @test
    async def target_empty_fs(self) -> None:
        target, tid = target_member(self, 50_003)
        await setup_author_spell(self.base_author.id, 1001, met_ids=[tid])
        await setup_target_user(tid, fs_cards=[])
        await invoke_use(self, 1001, target=target)
        assert_content_contains(self.base_context, "uses up")


class UseSpell1002(TestingUseSpell):
    @test
    async def success_starts_paginator(self) -> None:
        target, _ = await setup_met_view_spell(self, 1002, 50_004, fs_cards=[1011])
        await use_view_spell_paginator(self, 1002, target)

    @test
    async def not_met(self) -> None:
        target, _ = target_member(self, 50_005)
        await setup_author_spell(self.base_author.id, 1002)
        await invoke_use(self, 1002, target=target)
        assert_met_error(self.base_context)


class UseSpell1007(TestingUseSpell):
    @test
    async def steals_from_rs(self) -> None:
        target, tid = target_member(self, 50_007)
        await setup_author_spell(self.base_author.id, 1007)
        tu = await setup_target_user(tid, rs_cards=[STEAL_TARGET_CARD, 51])
        ensure_no_defense(tu)
        with patch_random_choice(STEAL_TARGET_CARD):
            await invoke_use(self, 1007, target=target)
        await assert_steal_succeeded(
            self.base_context,
            self.base_author.id,
            tid,
            STEAL_TARGET_CARD,
            message_fragment="Successfully stole",
        )

    @test
    async def no_rs_cards(self) -> None:
        target, _ = target_member(self, 50_008)
        await setup_author_spell(self.base_author.id, 1007)
        await invoke_use(self, 1007, target=target)
        assert_content_contains(self.base_context, "restricted slots")


class UseSpell1008(TestingUseSpell):
    @test
    async def swap_success(self) -> None:
        target, tid = target_member(self, 50_009)
        await setup_author_spell(self.base_author.id, 1008, extra_fs=[20])
        await setup_target_user(tid, fs_cards=[30], rs_cards=[40])
        with patch("killua.static.cards.random.choice", side_effect=[30, 20]):
            await invoke_use(self, 1008, target=target)
        assert_content_contains(self.base_context, "Successfully swapped")

    @test
    async def author_too_few_cards(self) -> None:
        target, tid = target_member(self, 50_010)
        await setup_author_spell(self.base_author.id, 1008)
        await setup_target_user(tid, fs_cards=[1011])
        await invoke_use(self, 1008, target=target)
        assert_content_contains(self.base_context, "other than card")


class UseSpell1010(TestingUseSpell):
    @test
    async def clone_success(self) -> None:
        await setup_author_spell(self.base_author.id, 1010, extra_fs=[11])
        await invoke_use(self, 1010, target=11)
        assert_content_contains(self.base_context, "Successfully added another copy")
        user = await reload_user(self.base_author.id)
        assert user.count_card(11) >= 2

    @test
    async def not_owned(self) -> None:
        await setup_author_spell(self.base_author.id, 1010)
        await invoke_use(self, 1010, target=11)
        assert_content_contains(self.base_context, "don't own")

    @test
    async def global_max(self) -> None:
        await setup_author_spell(self.base_author.id, 1010, extra_fs=[11])

        async def _many_owners(_self):
            return [1] * 10_000

        with patch.object(Card, "owners", _many_owners):
            await invoke_use(self, 1010, target=11)
        assert_content_contains(self.base_context, "maximum amount")


class UseSpell1011(TestingUseSpell):
    @test
    async def copy_from_target_rs(self) -> None:
        target, tid = target_member(self, 50_011)
        await setup_author_spell(self.base_author.id, 1011)
        await setup_target_user(tid, rs_cards=[STEAL_TARGET_CARD])

        async def _no_owners(_self):
            return []

        with patch.object(Card, "owners", _no_owners):
            await invoke_use(self, 1011, target=target)
        assert_content_contains(self.base_context, f"card No. {STEAL_TARGET_CARD}")

    @test
    async def target_no_rs(self) -> None:
        target, _ = target_member(self, 50_012)
        await setup_author_spell(self.base_author.id, 1011)
        await invoke_use(self, 1011, target=target)
        assert_content_contains(self.base_context, "uses up")


class UseSpell1015(TestingUseSpell):
    @test
    async def success_starts_paginator(self) -> None:
        target, _ = await setup_met_view_spell(self, 1015, 50_015, fs_cards=[1011])
        await use_view_spell_paginator(self, 1015, target)

    @test
    async def not_met(self) -> None:
        target, _ = target_member(self, 50_016)
        await setup_author_spell(self.base_author.id, 1015)
        await invoke_use(self, 1015, target=target)
        assert_met_error(self.base_context)


class UseSpell1018(TestingUseSpell):
    @test
    async def steals_when_history_has_victim(self) -> None:
        victim, vid = target_member(self, 50_018)
        await setup_author_spell(self.base_author.id, 1018)
        await setup_target_user(vid, rs_cards=[STEAL_TARGET_CARD])
        with seed_channel_history(self.base_context, [victim]):
            with patch_random_choice([STEAL_TARGET_CARD, {"fake": False, "clone": False}]):
                await invoke_use(self, 1018)
        assert_content_contains(self.base_context, str(STEAL_TARGET_CARD))
        await assert_inventory(self.base_author.id, has=[STEAL_TARGET_CARD])

    @test
    async def all_defend_or_empty(self) -> None:
        await setup_author_spell(self.base_author.id, 1018)
        with seed_channel_history(self.base_context, []):
            await invoke_use(self, 1018)
        assert_content_contains(self.base_context, "defend")


class UseSpell1020(TestingUseSpell):
    @test
    async def creates_fake(self) -> None:
        await setup_author_spell(self.base_author.id, 1020)
        await invoke_use(self, 1020, target=11)
        assert_content_contains(self.base_context, "Created a fake of card No. 11")

    @test
    async def card_id_zero(self) -> None:
        await setup_author_spell(self.base_author.id, 1020)
        await self.command(self.cog, self.base_context, item="1020", args=0)
        content = last_content(self.base_context)
        assert "between 1 and 99" in content or "less than 1" in content.lower()

    @test
    async def card_id_over_99(self) -> None:
        await setup_author_spell(self.base_author.id, 1020)
        await invoke_use(self, 1020, target=100)
        content = last_content(self.base_context).lower()
        assert "between 1 and 99" in content or "invalid" in content


class UseSpell1021(TestingUseSpell):
    @test
    async def steals_specific_card(self) -> None:
        target, tid = target_member(self, 50_021)
        await setup_author_spell(self.base_author.id, 1021)
        tu = await setup_target_user(tid, rs_cards=[STEAL_TARGET_CARD])
        ensure_no_defense(tu)
        await invoke_use(self, 1021, target=target, args=STEAL_TARGET_CARD)
        await assert_steal_succeeded(
            self.base_context,
            self.base_author.id,
            tid,
            STEAL_TARGET_CARD,
            message_fragment="Stole card number",
        )

    @test
    async def target_lacks_card(self) -> None:
        target, _ = target_member(self, 50_022)
        await setup_author_spell(self.base_author.id, 1021)
        await invoke_use(self, 1021, target=target, args=STEAL_TARGET_CARD)
        assert_content_contains(self.base_context, "doesn't have this card")

    @test
    async def card_id_zero(self) -> None:
        target, _ = target_member(self, 50_023)
        await setup_author_spell(self.base_author.id, 1021)
        await invoke_use(self, 1021, target=target, args=0)
        assert_content_contains(self.base_context, "less than 1")


class UseSpell1024(TestingUseSpell):
    @test
    async def removes_fakes_and_clones(self) -> None:
        target, tid = target_member(self, 50_024)
        await setup_author_spell(self.base_author.id, 1024)
        await setup_target_user(
            tid,
            fs_cards=[(1007, True, False), (1008, False, True)],
            rs_cards=[(STEAL_TARGET_CARD, True, False)],
        )
        await invoke_use(self, 1024, target=target)
        assert_content_contains(self.base_context, "Successfully removed")

    @test
    async def target_no_fakes(self) -> None:
        target, tid = target_member(self, 50_025)
        await setup_author_spell(self.base_author.id, 1024)
        await setup_target_user(tid, fs_cards=[1011])
        await invoke_use(self, 1024, target=target)
        assert_content_contains(self.base_context, "does not have any cards")


class UseSpell1026(TestingUseSpell):
    @test
    async def adds_protection_effect(self) -> None:
        await setup_author_spell(self.base_author.id, 1026)
        await invoke_use(self, 1026)
        assert_content_contains(
            self.base_context,
            "automatically protected from the next 10 attacks",
        )
        user = await reload_user(self.base_author.id)
        assert user.effects["1026"] == 10

    @test
    async def cancel_renew_confirm(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1026, extra_fs=[1026])
        await user.add_effect("1026", 5)
        self.base_context.timeout_view = False
        with respond_to_view(self.base_context, Testing.press_cancel):
            await invoke_use(self, 1026)
        assert_content_contains(self.base_context, "Successfully canceled")

    @test
    async def renew_confirm_success(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1026, extra_fs=[1026])
        await user.add_effect("1026", 5)
        self.base_context.timeout_view = False
        with respond_to_view(self.base_context, Testing.press_confirm):
            await invoke_use(self, 1026)
        assert_content_contains(
            self.base_context,
            "automatically protected from the next 10 attacks",
        )

    @test
    async def renew_confirm_timeout(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1026, extra_fs=[1026])
        await user.add_effect("1026", 5)
        self.base_context.timeout_view = True
        await invoke_use(self, 1026)
        assert_content_contains(self.base_context, "Timed out")


class UseSpell1028(TestingUseSpell):
    @test
    async def destroys_fs_card(self) -> None:
        target, tid = target_member(self, 50_028)
        await setup_author_spell(self.base_author.id, 1028)
        tu = await setup_target_user(tid, fs_cards=[1011, 1010])
        ensure_no_defense(tu)
        with patch_random_choice([1011, {"fake": False, "clone": False}]):
            await invoke_use(self, 1028, target=target)
        assert_content_contains(self.base_context, "destroyed card No. 1011")
        await assert_inventory(tid, lacks=[1011])

    @test
    async def no_fs_cards(self) -> None:
        target, _ = target_member(self, 50_029)
        await setup_author_spell(self.base_author.id, 1028)
        await invoke_use(self, 1028, target=target)
        assert_content_contains(self.base_context, "free slots")


class UseSpell1029(TestingUseSpell):
    @test
    async def destroys_rs_card(self) -> None:
        target, tid = target_member(self, 50_031)
        await setup_author_spell(self.base_author.id, 1029)
        tu = await setup_target_user(tid, rs_cards=[STEAL_TARGET_CARD, 51])
        ensure_no_defense(tu)
        with patch_random_choice([STEAL_TARGET_CARD, {"fake": False, "clone": False}]):
            await invoke_use(self, 1029, target=target)
        assert_content_contains(self.base_context, f"destroyed card No. {STEAL_TARGET_CARD}")
        await assert_inventory(tid, lacks=[STEAL_TARGET_CARD])

    @test
    async def no_rs_cards(self) -> None:
        target, _ = target_member(self, 50_032)
        await setup_author_spell(self.base_author.id, 1029)
        await invoke_use(self, 1029, target=target)
        assert_content_contains(self.base_context, "restricted slots")


class UseSpell1031(TestingUseSpell):
    @test
    async def sends_analysis_embed(self) -> None:
        await setup_author_spell(self.base_author.id, 1031)

        async def _no_owners(_self):
            return []

        with patch.object(Card, "owners", _no_owners):
            await invoke_use(self, 1031, target=11)
        assert_embed_title(embed_at(self.base_context), "Info about card 11")

    @test
    async def invalid_card(self) -> None:
        await setup_author_spell(self.base_author.id, 1031)
        await invoke_use(self, 1031, target=99999)
        assert_content_contains(self.base_context, "Specified card is invalid")


class UseSpell1032(TestingUseSpell):
    @test
    async def adds_random_card(self) -> None:
        await setup_author_spell(self.base_author.id, 1032)
        lottery_card = Card.find(
            lambda c: c["type"] == "normal"
            and c["available"] is True
            and c["rank"] != "SS"
            and c["id"] != 0
        )[0]

        async def _no_owners(_self):
            return []

        with patch_random_choice(lottery_card):
            with patch.object(Card, "owners", _no_owners):
                await invoke_use(self, 1032)
        assert_content_contains(self.base_context, "Successfully added card No.")

    @test
    async def full_free_slots(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1032)
        for i in range(FREE_SLOTS):
            try:
                await user.add_card(1000 + (i % 50))
            except Exception:  # inventory full or duplicate slot — stop seeding
                break
        await invoke_use(self, 1032)
        assert_content_contains(self.base_context, "don't have any space")


class UseSpell1035(TestingUseSpell):
    @test
    async def protects_page(self) -> None:
        await setup_author_spell(self.base_author.id, 1035)
        await invoke_use(self, 1035, target=3)
        assert_content_contains(self.base_context, "Page 3 is now permanently protected")
        user = await reload_user(self.base_author.id)
        assert user.has_effect("page_protection_3")[0]

    @test
    async def page_out_of_range(self) -> None:
        await setup_author_spell(self.base_author.id, 1035)
        await invoke_use(self, 1035, target=9)
        assert_content_contains(self.base_context, "between 1 and 6")

    @test
    async def already_protected(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1035)
        await user.add_effect("page_protection_2", datetime.now())
        await invoke_use(self, 1035, target=2)
        assert_content_contains(self.base_context, "already have this effect")


class UseSpell1036(TestingUseSpell):
    @test
    async def analysis_after_unlock(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1036)
        await user.add_effect("1036", datetime.now())

        async def _no_owners(_self):
            return []

        with patch.object(Card, "owners", _no_owners):
            await invoke_use(self, 1036, target="analysis", args=11)
        assert_embed_title(embed_at(self.base_context), "Info about card 11")

    @test
    async def invalid_effect(self) -> None:
        user = await setup_author_spell(self.base_author.id, 1036)
        await user.add_effect("1036", datetime.now())
        await invoke_use(self, 1036, target="bogus", args=11)
        assert_content_contains(self.base_context, "Invalid effect to use")

    @test
    async def not_unlocked(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await invoke_use(self, 1036, target="list", args=11)
        assert_content_contains(self.base_context, "need to have used the card 1036 once")


class UseSpell1038(TestingUseSpell):
    @test
    async def list_embed(self) -> None:
        await setup_author_spell(self.base_author.id, 1038)

        async def _no_owners(_self):
            return []

        with patch.object(Card, "owners", _no_owners):
            await invoke_use(self, 1038, target=11)
        assert_embed_title(embed_at(self.base_context), "Infos about card")

    @test
    async def card_id_zero(self) -> None:
        await setup_author_spell(self.base_author.id, 1038)
        await self.command(self.cog, self.base_context, item="1038", args=0)
        assert_content_contains(self.base_context, "less than 1")

    @test
    async def invalid_card(self) -> None:
        await setup_author_spell(self.base_author.id, 1038)
        await invoke_use(self, 1038, target=99999)
        assert_content_contains(self.base_context, "Specified card is invalid")


class UseDefense1003(TestingUseSpell):
    @test
    async def blocks_attack(self) -> None:
        _, tid = await run_attack_against_defender(self, defense_id=1003)
        await assert_steal_blocked_by_defense(
            self.base_context, self.base_author.id, tid, STEAL_TARGET_CARD
        )

    @test
    async def attack_proceeds_on_timeout(self) -> None:
        _, tid = await run_attack_against_defender(
            self, defense_id=1003, use_defense=False
        )
        assert "successfully defended" not in last_content(self.base_context).lower()
        await assert_steal_succeeded(
            self.base_context,
            self.base_author.id,
            tid,
            STEAL_TARGET_CARD,
            message_fragment="Stole",
        )


class UseDefense1004(TestingUseSpell):
    @test
    async def blocks_when_met(self) -> None:
        _, tid = await run_attack_against_defender(
            self, defense_id=1004, attacker_in_met=True
        )
        await assert_steal_blocked_by_defense(
            self.base_context, self.base_author.id, tid, STEAL_TARGET_CARD
        )

    @test
    async def attack_succeeds_when_not_met(self) -> None:
        target, tid = target_member(self, 50_104)
        await setup_author_spell(self.base_author.id, DEFAULT_ATTACK_SPELL)
        await setup_target_user(
            tid,
            rs_cards=[STEAL_TARGET_CARD],
            defense_ids=[1004],
            met_attacker=False,
        )
        await invoke_use(
            self, DEFAULT_ATTACK_SPELL, target=target, args=STEAL_TARGET_CARD
        )
        await assert_steal_succeeded(
            self.base_context,
            self.base_author.id,
            tid,
            STEAL_TARGET_CARD,
            message_fragment="Stole card number",
        )


class UseDefense1019(TestingUseSpell):
    @test
    async def blocks_sr_attack(self) -> None:
        _, tid = await run_attack_against_defender(
            self, defense_id=1019, patch_attacker_range="SR"
        )
        await assert_steal_blocked_by_defense(
            self.base_context, self.base_author.id, tid, STEAL_TARGET_CARD
        )

    @test
    async def no_block_non_sr_range(self) -> None:
        _, tid = await run_attack_against_defender(
            self, defense_id=1019, patch_attacker_range="B"
        )
        await assert_steal_succeeded(
            self.base_context,
            self.base_author.id,
            tid,
            STEAL_TARGET_CARD,
            message_fragment="Stole card number",
        )


class UseDefense1025(TestingUseSpell):
    @test
    async def blocks_view_spell(self) -> None:
        target, tid = target_member(self, 50_125)
        await setup_author_spell(self.base_author.id, 1001, met_ids=[tid])
        await setup_target_user(
            tid,
            fs_cards=[1011],
            defense_ids=[1025],
            met_attacker=True,
            attacker_id=self.base_author.id,
        )

        async def _def(ctx):
            await respond_defense_with_spell(ctx, 1025)

        with respond_to_view(self.base_context, _def):
            await invoke_use(self, 1001, target=target)
        assert_content_contains(self.base_context, "successfully defended")
        await assert_inventory(tid, has=[1011])
