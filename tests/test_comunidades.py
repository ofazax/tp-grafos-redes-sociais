
from redes.comunidades.modularidade import modularidade
from redes.comunidades.louvain import louvain
from redes.comunidades.rotulos import propagacao_de_rotulos
from redes.co
ent / "dados" / "karate_arestas.txt"
ARQUIVO_CLUBES = Path(__file__).parent / "dados" / "karate_clubes.txt"


def carregar_karate_e_clubes() -> tuple[Grafo, dict[int, int]]:
    g = GraeR a in f:
 linha.strip()
                continue
            u, v = linha.split()
            g.adicionar_aresta(int(u), int(v))

    particao_real: dict[int, int] = {}
    with open(ARQUIVO_CLUBES, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            no, faccao = linha.split()
            particao_real[int(no)] = int(faccao)

    return g, particao_real


# -------------------------------------------------------------
# Testes com casos teóricos de modularidade
# -------------------------------------------------------------

def test_modularidade_grafo_vazio():
    g = Grafo()
    assert modularidade(g, {}) == 0.0

i: tnam), (2 4: 1, 5: 1}
ert modularidade(g, particao) == pytest.approx(0.5)


    g, particao_real = carregar_karate_e_clubes()
    q = modularidade(g, particao_real)
    assert q == pytest.approx(0.3582, abs=1e-3)


# -------------------------------------------------------------
# Testes do algoritmo de Louvain
# -------------------------------------------------------------

def test_louvain_grafo_vazio():
    g = Grafo()
    particao, q = louvain(g)
    assert particao == {}
    assert q == 0.0


def test_louvain_particao_valida():
    g, _ = carregar_karate_e_clubes()
    particao, q = louvain(g)
    assert set(particao.keys()) == set(g.nos())
    assert all(isinstance(c, int) for c in particao.values())


def test_louvain_determinismo():
    g, _ = carregar_karate_e_clubes()
    p1, q1 = louvain(g, semente=42)

def test_louvain_q_karate():
    g, _ = carregar_karate_e_clubes().42]"


def test_louvain_q_maior_que_divisao_real():
    g, particao_real = carregar_karate_e_clubes()
    q_real = modularidade(g, particao_real)
    _, q_louvain = louvain(g, semente=42)
    assert q_louvain > q_real, (
        f"Louvain (Q={q_louvain:.4f}) não superou a divisão real (Q={q_real:.4f})"
    )


# -------------------------------------------------------------
# Testes de Propagação de Rótulos (LPA)
# -------------------------------------------------------------

    g = Grafo()
    assert propagacao_de_rot

def test_rotulos_particao_valida():    g, _ = carregar_karate_e_clubes()
    particao = propagacao_de_rotulos(g)
et(particao.keys()) == set(g.nos())
    assert all(isinstance(c, int) for c in particao.values())


def test_rotulos_determinismo():
    g, _ = carregar_karate_e_clubes()
    p1 = propagacao_de_rotulos(g, semente=7)
    p2 = propagacao_de_rotulos(g, semente=7)
    assert p1 == p2


# -------------------------------------------------------------
# Testes de Avaliação (NMI, ARI)
# -------------------------------------------------------------

def test_nmi_particoes_identicas():
    p = {0: 0, 1: 0, 2: 1, 3: 1}
    assert nmi(p, p) == pytest.approx(1.0)


def test_nmi_particoes_independentes():
    p1 = {0: 0, 1: 0, 2: 1, 3: 1}
    p2 = {0: 0, 1: 1, 2: 0, 3: 1}
    assert nmi(p1, p2) == pytest.approx(0.0, abs=1e-9)


def test_ari_particoes_identicas():
    p = {0: 0, 1: 0, 2: 1, 3: 1}
    assert ari(p, p) == pytest.approx(1.0)


def test_ari_particoes_independentes():
    rng = random.Random(42)
    n_nos = 500
    p1 = {i: rng.randint(0, 3) for i in range(n_nos)}
    p2 = {i: rng.randint(0, 3) for i in range(n_nos)}
    assert ari(p1, p2) == pytest.approx(0.0, abs=0.05)


def test_ari_particoes_opostas_negativo():
    p1 = {0: 0, 1: 0, 2: 1, 3: 1}
    p2 = {0: 0, 1: 1, 2: 0, 3: 1}
    assert ari(p1, p2) == pytest.approx(-0.5)
