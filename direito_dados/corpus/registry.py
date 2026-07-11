"""Static registry of the federal criminal-law microsystem (9 norms)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NormSpec:
    id: str
    title: str
    norm_type: str
    source_url: str
    filename: str
    urn: str = ""
    domain: str = "penal"


def _spec(id_, title, norm_type, url, urn):
    return NormSpec(id=id_, title=title, norm_type=norm_type, source_url=url,
                    filename=f"{id_}.txt", urn=urn, domain="penal")


NORMS: dict[str, NormSpec] = {
    s.id: s
    for s in [
        _spec("CF", "Constituição Federal de 1988", "constituicao",
              "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
              "urn:lex:br:federal:constituicao:1988-10-05"),
        _spec("CP", "Código Penal (DL 2.848/1940)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
              "urn:lex:br:federal:decreto.lei:1940-12-07;2848"),
        _spec("CPP", "Código de Processo Penal (DL 3.689/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm",
              "urn:lex:br:federal:decreto.lei:1941-10-03;3689"),
        _spec("LEP", "Lei de Execução Penal (7.210/1984)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l7210compilado.htm",
              "urn:lex:br:federal:lei:1984-07-11;7210"),
        _spec("L11343", "Lei de Drogas (11.343/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11343.htm",
              "urn:lex:br:federal:lei:2006-08-23;11343"),
        _spec("L11340", "Lei Maria da Penha (11.340/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm",
              "urn:lex:br:federal:lei:2006-08-07;11340"),
        _spec("L8072", "Crimes Hediondos (8.072/1990)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm",
              "urn:lex:br:federal:lei:1990-07-25;8072"),
        _spec("DL3688", "Contravenções Penais (DL 3.688/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm",
              "urn:lex:br:federal:decreto.lei:1941-10-03;3688"),
        _spec("LINDB", "LINDB (DL 4.657/1942)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm",
              "urn:lex:br:federal:decreto.lei:1942-09-04;4657"),
    ]
}
