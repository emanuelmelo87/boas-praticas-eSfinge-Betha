"""
Cliente Python para a API e-Sfinge TCE/SC (Módulo Tributário)

Uso:
    from tce_sc_client import EsfingeClient

    client = EsfingeClient(codigo_ug="12300", codigo_acesso="07460949906", senha="suasenha")
    client.autenticar()

    # Consultar unidades gestoras
    ugs = client.unidades_gestoras()

    # Consultar remessas por data
    remessas = client.consultar_por_data("2025-01-01", "2025-01-31")

    # Consultar status de lotes de uma chave de pacote
    lotes = client.status_lote(chave_pacote="abc123")

    # Listar mensagens do sistema
    msgs = client.mensagens()
"""

import os
import requests
from datetime import datetime
from typing import Optional


URLS = {
    "producao": "https://api.virtual.tce.sc.gov.br",
    "testes":   "https://virtual.testing.tce.sc.gov.br",
}


class EsfingeClient:
    def __init__(
        self,
        codigo_ug: str,
        codigo_acesso: str,
        senha: str,
        descricao_empresa_ti: str = "BETHA SISTEMAS LTDA",
        descritivo_software: str = "PRESTAÇÃO DE CONTAS",
    ):
        self.codigo_ug = str(codigo_ug)
        self.codigo_acesso = codigo_acesso
        self.senha = senha
        self.descricao_empresa_ti = descricao_empresa_ti
        self.descritivo_software = descritivo_software

        # Ambiente determinado pela senha (igual ao comportamento do Postman)
        self.base_url = URLS["testes"] if senha == "123456" else URLS["producao"]

        self.token: Optional[str] = None
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Autenticação                                                         #
    # ------------------------------------------------------------------ #

    def autenticar(self) -> str:
        """Autentica na API e armazena o token internamente. Retorna o token."""
        url = f"{self.base_url}/esfingeonline/autenticacao/login"
        params = {
            "codigoUg": self.codigo_ug,
            "descricaoEmpresaTI": self.descricao_empresa_ti,
            "descritivoSoftware": self.descritivo_software,
        }
        headers = {
            "codigoAcesso": self.codigo_acesso,
            "senha": self.senha,
        }
        resp = self._session.post(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        self.token = data["chave"]
        print(f"[OK] Autenticado em {self.base_url} — token obtido.")
        return self.token

    def _headers(self) -> dict:
        if not self.token:
            raise RuntimeError("Chame autenticar() antes de usar os endpoints.")
        return {
            "AUTH_TOKEN": self.token,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> any:
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict = None, params: dict = None) -> any:
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, headers=self._headers(), json=body, params=params)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Serviços Gerais (consulta)                                           #
    # ------------------------------------------------------------------ #

    def unidades_gestoras(self) -> list:
        """Lista as unidades gestoras disponíveis para o usuário."""
        return self._get("/esfingeonline/servicosGerais/getUnidadesGestoras")

    def mensagens(self) -> list:
        """Retorna as mensagens do sistema para o usuário autenticado."""
        return self._get("/esfingeonline/servicosGerais/getMensagens")

    def consultar_por_data(self, data_inicio: str, data_fim: str) -> list:
        """
        Consulta remessas enviadas no período.

        Args:
            data_inicio: "YYYY-MM-DD"
            data_fim:    "YYYY-MM-DD"
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim}
        return self._get("/esfingeonline/servicosGerais/consultarPorData", params=params)

    def status_lote(self, chave_pacote: str) -> list:
        """
        Consulta o status de todos os lotes de uma chave de pacote.

        Situações possíveis: RECEBIDO, EM_PROCESSAMENTO, PROCESSADO_SUCESSO,
        PROCESSADO_ERRO_NEGOCIO, PROCESSADO_ERRO_INTERNO, ABORTADO,
        ABORTADO_ERRO_LOTE_ANTERIOR.
        """
        path = f"/esfingeonline/servicosGerais/consultarStatusLotePorChavePacote/{chave_pacote}"
        return self._get(path)

    # ------------------------------------------------------------------ #
    # Notas Fiscais (consulta)                                             #
    # ------------------------------------------------------------------ #

    def consultar_nfse_por_lote(self, numero_lote: int) -> dict:
        """Consulta NFS-e pelo número do lote."""
        path = f"/esfingeonline/v5/notafiscal/consultarPorNumeroLote/{numero_lote}"
        return self._get(path)

    # ------------------------------------------------------------------ #
    # Tributário V5 (consulta)                                             #
    # ------------------------------------------------------------------ #

    def consultar_tributario_por_lote(self, numero_lote: int) -> dict:
        """Consulta dados tributários pelo número do lote."""
        path = f"/esfingeonline/v5/tributario/consultarPorNumeroLote/{numero_lote}"
        return self._get(path)

    # ------------------------------------------------------------------ #
    # Listar Pacotes (extrato remessa online)                              #
    # ------------------------------------------------------------------ #

    def listar_pacotes(
        self,
        data_inicial: str,
        data_final: str,
        identificador_ugs: list[int],
        identificador_modulo: int = 20,
        identificador_assunto: int = 40,
        identificador_informacao_fase: int = 46,
        identificadores_remessas: list[int] = None,
        identificacao_informacao: str = "",
        codigo_registro: str = None,
        page: int = 0,
    ) -> dict:
        """
        Lista pacotes enviados via extrato de remessa online.

        Args:
            data_inicial:  "YYYY-MM-DDTHH:MM:SS.000Z"
            data_final:    "YYYY-MM-DDTHH:MM:SS.000Z"
            identificador_ugs: lista de IDs de UGs, ex: [441]
            page: página (paginação, começa em 0)
        """
        body = {
            "codigoRegistro": codigo_registro,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "identificadorModulo": identificador_modulo,
            "identificadorAssunto": identificador_assunto,
            "identificadorInformacaoFase": identificador_informacao_fase,
            "identificadorUGs": identificador_ugs,
            "identificacaoInformacao": identificacao_informacao,
            "identificadoresRemessas": identificadores_remessas or [],
            "page": page,
        }
        return self._post(
            "/esfingeweb/rest/extratoRemessaOnline/listarInformacao/",
            body=body,
        )


# ------------------------------------------------------------------ #
# Execução direta — demonstração rápida                               #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    # Leia as credenciais de variáveis de ambiente ou edite aqui diretamente
    UG     = os.getenv("TCE_CODIGO_UG",     "")   # ex: "12300"
    ACESSO = os.getenv("TCE_CODIGO_ACESSO", "")   # ex: CPF sem pontos
    SENHA  = os.getenv("TCE_SENHA",         "")   # senha real ou "123456" p/ testes

    if not all([UG, ACESSO, SENHA]):
        print("Defina as variáveis de ambiente TCE_CODIGO_UG, TCE_CODIGO_ACESSO e TCE_SENHA")
        print("  Exemplo (PowerShell):")
        print("    $env:TCE_CODIGO_UG     = '12300'")
        print("    $env:TCE_CODIGO_ACESSO = '07460949906'")
        print("    $env:TCE_SENHA         = '123456'   # testes")
        raise SystemExit(1)

    client = EsfingeClient(codigo_ug=UG, codigo_acesso=ACESSO, senha=SENHA)
    client.autenticar()

    # --- Unidades gestoras ---
    print("\n=== Unidades Gestoras ===")
    import json
    ugs = client.unidades_gestoras()
    print(json.dumps(ugs, indent=2, ensure_ascii=False))

    # --- Mensagens do sistema ---
    print("\n=== Mensagens ===")
    msgs = client.mensagens()
    print(json.dumps(msgs, indent=2, ensure_ascii=False))

    # --- Remessas dos últimos 30 dias ---
    from datetime import timedelta
    hoje = datetime.today()
    inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
    fim = hoje.strftime("%Y-%m-%d")
    print(f"\n=== Remessas de {inicio} a {fim} ===")
    remessas = client.consultar_por_data(inicio, fim)
    print(json.dumps(remessas, indent=2, ensure_ascii=False))
