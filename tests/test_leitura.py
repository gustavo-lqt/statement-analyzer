from __future__ import annotations

import pytest

from app.leitura import ler
from app.models import ArquivoVazio, EncodingInvalido, FichaBanco, NenhumaLinhaValida, Recusa
from app.regras import normalizar, processar


def test_leitura_aplica_cabecalho_e_preserva_delimitador_em_campo_quoted(ficha):
    """Verifica RF01 quando a descrição contém o delimitador protegido por aspas CSV."""
    payload = 'Data;Historico;Valor\n01/09/2026;"ITEM; SINTETICO";1,00\n'.encode()
    result = processar(ler(payload, ficha), ficha)
    assert result.lancamentos[0].descricao == "ITEM; SINTETICO"


def test_leitor_marca_registro_com_colunas_a_menos(ficha):
    """Verifica RN05 para registro CSV truncado sem abortar registros válidos subsequentes."""
    payload = (
        "Data;Historico;Valor\n"
        "01/09/2026;INCOMPLETO\n"
        "02/09/2026;COMPLETO;2,00\n"
    ).encode()
    result = processar(ler(payload, ficha), ficha)
    assert result.recusas[0].motivo == "LINHA_TRUNCADA"
    assert result.recusas[0].numero_linha == 2
    assert len(result.lancamentos) == 1


def test_leitor_marca_registro_com_colunas_extras(ficha):
    """Verifica RN05 para registro cujo número de campos não corresponde ao cabeçalho."""
    payload = "Data;Historico;Valor\n01/09/2026;ITEM;1,00;EXTRA\n".encode()
    result = normalizar(next(iter(ler(payload, ficha))), ficha)
    assert isinstance(result, Recusa)
    assert result.motivo == "LINHA_TRUNCADA"


def test_cabecalho_sem_coluna_declarada_gera_recusa(ficha):
    """Verifica RN05 e COLUNA_AUSENTE quando o cabeçalho não contém coluna configurada."""
    payload = "Data;Outra;Valor\n01/09/2026;X;1,00\n".encode()
    result = normalizar(next(iter(ler(payload, ficha))), ficha)
    assert isinstance(result, Recusa)
    assert result.motivo == "COLUNA_AUSENTE"


def test_encoding_latin1_declara_ficha_sem_inferir(ficha):
    """Verifica RN01 e RF01 respeitando o encoding explicitamente declarado na ficha."""
    latin_ficha = FichaBanco(
        ficha.nome,
        ficha.delimitador,
        "latin-1",
        ficha.formato_data,
        ficha.separador_decimal,
        ficha.separador_milhar,
        ficha.convencao_sinal,
        ficha.colunas,
    )
    payload = "Data;Historico;Valor\n01/09/2026;Café;1,00\n".encode("latin-1")
    result = processar(ler(payload, latin_ficha), latin_ficha)
    assert result.lancamentos[0].descricao == "Café"


def test_encoding_invalido_gera_erro_tipado(ficha):
    """Verifica o contrato ENCODING_INVALIDO em vez de inferir outra codificação."""
    with pytest.raises(EncodingInvalido):
        list(ler(b"\xff", ficha))


def test_arquivo_vazio_gera_erro_tipado(ficha):
    """Verifica o contrato ARQUIVO_VAZIO para conteúdo sem bytes."""
    with pytest.raises(ArquivoVazio):
        ler(b"", ficha)


def test_arquivo_com_apenas_cabecalho_levanta_rn06(ficha):
    """Verifica RN06 quando nenhum registro válido existe após o cabeçalho."""
    payload = "Data;Historico;Valor\n".encode()
    with pytest.raises(NenhumaLinhaValida):
        processar(ler(payload, ficha), ficha)