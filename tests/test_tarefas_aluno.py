"""TAREFA DO ALUNO -- os cinco testes que faltam para os >= 8 do entregavel.

Cada teste abaixo tem nome, docstring e um pytest.skip. Apague o skip, escreva o
corpo, e o teste passa a valer. Nenhum deles precisa de banco: os tres primeiros
rodam so contra o motor.
"""

from __future__ import annotations

from decimal import Decimal

import pytest


def test_regressao_numerica_contra_a_planilha(fluxos_golden):
    """Compara os seis indices com os valores esperados do inventario golden."""
    from app.dominio.motor_emergia import calcular_indices

    resultado = calcular_indices(
        fluxos_golden,
        Decimal("1000"),
    )

    esperados = {
        "y": Decimal("200.000000"),
        "eyr": Decimal("4.000000"),
        "elr": Decimal("0.739130"),
        "esi": Decimal("5.411765"),
        "eii": Decimal("0.184783"),
        "percentual_r": Decimal("57.500000"),
    }

    for nome, esperado in esperados.items():
        atual = getattr(resultado, nome)
        assert abs(atual - esperado) <= Decimal("1E-6"), (
            f"{nome}: esperado {esperado}, obtido {atual}"
        )


def test_quantizacao_unica_no_final():
    """Prova que arredondar EYR e ELR antes da divisão altera o ESI."""
    from decimal import ROUND_HALF_EVEN, localcontext

    eyr = Decimal("123.456789123")
    elr = Decimal("7.891234567")

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN

        # Forma errada: arredonda os valores intermediarios.
        eyr_arredondado = eyr.quantize(Decimal("1E-6"))
        elr_arredondado = elr.quantize(Decimal("1E-6"))
        esi_com_arredondamento_intermediario = (
            eyr_arredondado / elr_arredondado
        ).quantize(Decimal("1E-6"))

        # Forma correta: calcula com precisao e arredonda somente no final.
        esi_sem_arredondamento_intermediario = (
            eyr / elr
        ).quantize(Decimal("1E-6"))

    assert esi_com_arredondamento_intermediario != esi_sem_arredondamento_intermediario

def test_ordem_da_soma_com_magnitudes_divergentes():
    """Exercita a perda de associatividade com magnitudes muito diferentes."""
    from decimal import localcontext

    grande = Decimal("1E20")
    pequeno = Decimal("1E-5")
    compensacao = Decimal("-99999999999999999999")

    with localcontext() as ctx:
        ctx.prec = 10

        primeira_ordem = (grande + pequeno) + compensacao
        segunda_ordem = grande + (pequeno + compensacao)

    assert primeira_ordem != segunda_ordem
    
def test_erro_de_dominio_responde_problem_json(cliente, corpo_golden):
    """Inventario sem fluxo renovavel deve sair 422 em application/problem+json."""
    corpo = corpo_golden.copy()

    corpo["fluxos"] = [
        {
            "recurso": "solo",
            "categoria": "N",
            "emergia_sej": "50",
        },
        {
            "recurso": "diesel",
            "categoria": "MN",
            "emergia_sej": "20",
        },
    ]

    resposta = cliente.post(
        "/v1/safras/42/calculos",
        json=corpo,
    )

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(
        "application/problem+json"
    )

    problema = resposta.json()

    assert problema["type"]
    assert problema["title"]
    assert problema["status"] == 422
    assert problema["detail"]
    assert problema["instance"] == "/v1/safras/42/calculos"

def test_campo_extra_no_corpo_da_requisicao_e_rejeitado(cliente, corpo_golden):
    """Campo desconhecido no corpo deve ser rejeitado com 422."""
    corpo = corpo_golden.copy()
    corpo["energia_produto_jj"] = "1000"

    resposta = cliente.post(
        "/v1/safras/42/calculos",
        json=corpo,
    )

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(
        "application/problem+json"
    )

    problema = resposta.json()

    assert problema["type"]
    assert problema["title"]
    assert problema["status"] == 422
    assert problema["detail"]
    assert problema["instance"] == "/v1/safras/42/calculos"

    assert "erros" in problema
    assert any(
        erro["campo"] == "body.energia_produto_jj"
        for erro in problema["erros"]
    )