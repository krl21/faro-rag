from app.ai.rag.guardrails import check_answer


def test_valid_citations_are_renumbered_in_order_of_appearance():
    checked = check_answer("Cubre robo [2] e incendio [1][2].", fragment_count=3)
    assert checked.has_evidence
    assert checked.text == "Cubre robo [1] e incendio [2][1]."
    assert checked.cited == [2, 1]  # Marker [1] -> fragment 2, marker [2] -> fragment 1.


def test_out_of_range_citations_are_removed():
    checked = check_answer("Cubre robo [1] y daños [7].", fragment_count=2)
    assert checked.cited == [1]
    assert checked.text == "Cubre robo [1] y daños ."


def test_no_evidence_token_means_no_answer():
    assert not check_answer("NO_EVIDENCE", fragment_count=3).has_evidence


def test_answer_without_valid_citations_is_rejected():
    assert not check_answer("La póliza cubre todo.", fragment_count=3).has_evidence
    assert not check_answer("Cubre todo [9].", fragment_count=3).has_evidence


def test_empty_answer_is_rejected():
    assert not check_answer("   ", fragment_count=3).has_evidence


def test_repeated_citation_is_listed_once():
    assert check_answer("A [1]. B [1].", fragment_count=1).cited == [1]


def test_citation_zero_is_invalid():
    checked = check_answer("Dato [0] y otro [1].", fragment_count=2)
    assert checked.cited == [1]
    assert "[0]" not in checked.text


def test_no_evidence_token_inside_text_rejects_the_answer():
    assert not check_answer("Lo siento. NO_EVIDENCE", fragment_count=2).has_evidence


def test_example_with_two_citations_uses_markers_one_and_two():
    checked = check_answer(
        "Cuatro líneas [5]. Venden 1.200 vehículos al año [1].", fragment_count=6
    )
    assert checked.text == "Cuatro líneas [1]. Venden 1.200 vehículos al año [2]."
    assert checked.cited == [5, 1]


def test_repeated_citation_keeps_its_new_number():
    checked = check_answer("A [4]. B [2]. C [4].", fragment_count=6)
    assert checked.text == "A [1]. B [2]. C [1]."
    assert checked.cited == [4, 2]


def test_no_marker_is_greater_than_the_number_of_citations():
    import re

    checked = check_answer("x [6] y [3] z [6] w [5] v [2]", fragment_count=6)
    markers = {int(m) for m in re.findall(r"\[(\d+)\]", checked.text)}
    assert markers == set(range(1, len(checked.cited) + 1))
