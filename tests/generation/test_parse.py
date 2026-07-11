from direito_dados.generation.parse import ParsedAnswer, parse_answer


def test_parses_clean_json():
    raw = '{"answer":"Homicídio é matar alguém.","citations":["CP:art121"],"hierarchy_notes":"","abstained":false,"confidence":0.9}'
    p = parse_answer(raw)
    assert p.parse_ok and not p.abstained
    assert p.answer.startswith("Homicídio")
    assert p.citations == ["CP:art121"] and p.confidence == 0.9


def test_parses_json_inside_fences_and_prose():
    raw = 'Claro!\n```json\n{"answer":"x","citations":["[CP:art155]"],"hierarchy_notes":"n","abstained":false,"confidence":0.5}\n```\nfim'
    p = parse_answer(raw)
    assert p.parse_ok
    assert p.citations == ["CP:art155"]   # brackets stripped


def test_unparseable_output_abstains_safely():
    p = parse_answer("desculpe, não consigo responder")
    assert not p.parse_ok and p.abstained and p.citations == [] and p.confidence == 0.0
