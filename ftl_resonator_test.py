# ============================================================
# FTL π-RESONATOR SIM — Monolithic Test Block with Diagnostics
# ============================================================

import math
import random

# ================================================================
# 0. CONFIGURATION
# ================================================================
CONFIG = {
    "kernel": {
        "volume_decay_base_min": 0.986,
        "volume_decay_base_max": 0.992,
        "volume_rebound_chance": 0.08,
        "critical_compression": 1.12,
    },
    "motifs": {
        "bead_threshold_sigma": 1.2,
        "resonance_density_threshold": 0.25,
        "resonance_Z_boost": 3.2,
        "resonance_F_boost": 1.22,
        "gate_999_L_boost": 3.5,
        "gate_999_T_drop": 4,
    },
    "topology": {
        "warp_rewire_prob": 0.15,
        "warp_remove_bias": 0.6,
        "warp_add_bias": 0.4,
    },
    "attention": {
        "attention_threshold": 0.5,
        "intent_feedback_strength": 0.15,
        "compression_sensitivity": 1.0,
    },
    "pi": {
        "pi_length": 1000,
        "resonance_window": 12,
    },
    "payload_weights": {
        "bead_weight": 1.0,
        "highway_weight": 2.0,
        "resonance_weight": 3.0,
        "gate_weight": 2.0,
    },
    "diagnostics": {
        "log_interval": 40,                # every 40 ticks for less spam
        "verbose": True,
        "log_to_gmf": True,
        "attractor_trigger_stability": 0.35,
        "attractor_trigger_compression": 5.0,
    }
}

# ================================================================
# 1. PI DIGITS
# ================================================================
def get_pi_digits(n=1000):
    pi_dec = (
        "1415926535897932384626433832795028841971693993751058209749445923078164062862089"
        "9862803482534211706798214808651328230664709384460955058223172535940812848111745"
        "0284102701938521105559644622948954930381964428810975665933446128475648233786783"
        "1652712019091456485669234603486104543266482133936072602491412737245870066063155"
        "8817488152092096282925409171536436789259036001133053054882046652138414695194151"
        "1609433057270365759591953092186117381932611793105118548074462379962749567351885"
        "7527248912279381830119491298336733624406566430860213949463952247371907021798609"
        "4370277053921717629317675238467481846766940513200056812714526356082778577134275"
        "7789609173637178721468440901224953430146549585371050797279689258923542019956112"
        "1290219608640344181598136297747713099605187072113499999983729780499510597317328"
        "1609631859502445945534690830264252230825334468503526193118817101000313783875288"
        "6587533208382064171776914730359825349042875546873115956286388235378759375195778"
        "18577805321712268066130019278766111959092164201989"
    )
    digits = [int(c) for c in pi_dec[:n-1]]
    return [3] + digits

# ================================================================
# 2. CORE STRUCTURES & HELPERS
# ================================================================
def init_sim_pack(pi_digits):
    N = len(pi_digits)
    d = pi_digits[:]
    L = [1.0] * N
    F = [1.0 + random.uniform(-0.10, 0.15) for _ in range(N)]
    T = [1] * N
    Z = [1.0] * N
    return L, F, T, Z, d

def make_kernel_state():
    return {
        "ω": 1.0,
        "γ": 0.1,
        "R_max": 1.0,
        "w": 3.0,
        "s": 1.0,
        "α": 0.5,
        "β": 2.0,
        "volume": 1.0
    }

def init_topology(num_nodes):
    A = [[0] * num_nodes for _ in range(num_nodes)]
    W = [[0.0] * num_nodes for _ in range(num_nodes)]
    for i in range(num_nodes):
        j = (i + 1) % num_nodes
        A[i][j] = A[j][i] = 1
        W[i][j] = W[j][i] = 0.5
    return A, W

def topology_hash(A):
    return hash(tuple(tuple(row) for row in A))

def init_gmf():
    return {
        "attractor_traces": [],
        "warp_log": [],
        "topology_snapshots": [],
        "mode_heatmap": {},
        "diagnostics": []
    }

def init_collective_state():
    return {
        "intent": [0.25, 0.35, 0.45, 0.55, 0.30, 0.65],
        "attention": [0.0] * 6,  # placeholder size
        "last_mode": [0.0] * 6
    }

def make_bead(payload, topo_sig, kernel):
    compression = compute_compression(payload, kernel)
    return {
        "payload": payload,
        "topo_sig": topo_sig,
        "kernel": kernel,
        "compression": compression,
        "entangled_link": None
    }

# ================================================================
# 3. KERNEL & TOPOLOGY DYNAMICS
# ================================================================
def evolve_kernel(prev_kernel, payload_size, beads, highways, resonances, gates):
    k = dict(prev_kernel)
    k["ω"] *= (1.0 + 0.001 * payload_size)
    k["R_max"] *= (1.0 + 0.002 * payload_size)

    base_decay = random.uniform(
        CONFIG["kernel"]["volume_decay_base_min"],
        CONFIG["kernel"]["volume_decay_base_max"]
    )
    resonance_bonus = sum(r["density"] for r in resonances)
    gate_bonus = len(gates) * 0.3
    shrink_factor = 1.0 / (1.0 + 0.12 * (resonance_bonus + gate_bonus))
    k["volume"] *= base_decay * shrink_factor

    k["volume"] = max(0.08, k["volume"])
    if k["volume"] < 0.12 and random.random() < CONFIG["kernel"]["volume_rebound_chance"]:
        k["volume"] *= 2.2

    return k

def compute_compression(payload, kernel):
    w = CONFIG["payload_weights"]
    count = (
        len(payload["beads"]) * w["bead_weight"] +
        len(payload["highways"]) * w["highway_weight"] +
        len(payload["resonances"]) * w["resonance_weight"] +
        len(payload["gates"]) * w["gate_weight"]
    )
    base_size = 1.0 + count * 0.35
    return base_size / max(0.08, kernel["volume"])

def bead_is_critical(compression):
    return compression >= CONFIG["kernel"]["critical_compression"]

def warp_rewire(A, node_index, compression):
    cfg = CONFIG["topology"]
    N = len(A)
    p = cfg["warp_rewire_prob"] * min(0.35, max(0.0, compression - 0.8))
    old_edges = sum(sum(row) for row in A) // 2

    for j in range(N):
        if j == node_index:
            continue
        if random.random() < p:
            if random.random() < cfg["warp_remove_bias"]:
                if A[node_index][j] == 1:
                    A[node_index][j] = A[j][node_index] = 0
            else:
                if random.random() < cfg["warp_add_bias"]:
                    A[node_index][j] = A[j][node_index] = 1

    new_edges = sum(sum(row) for row in A) // 2
    return A, new_edges - old_edges

# ================================================================
# 4. MODE & ATTENTION
# ================================================================
def compute_mode_from_bead(bead, L, F, d, index):
    k = bead["kernel"]
    S_ω = k["ω"] / 10.0
    S_R = k["R_max"] / 10.0
    L_min, L_max = min(L), max(L)
    S_L = (L[index] - L_min) / max(1e-6, L_max - L_min)
    F_mean = sum(F) / len(F)
    S_F = F[index] / max(1e-6, F_mean)
    S_const = d[index] / 9.0
    sens = CONFIG["attention"]["compression_sensitivity"]
    S_Δ = math.tanh(sens * bead["compression"])
    return [S_ω, S_R, S_L, S_F, S_const, S_Δ]

def update_attention(collective, MODES):
    intent = collective["intent"]
    norm_i = math.sqrt(sum(x*x for x in intent)) or 1e-6
    att = []
    for mode in MODES:
        dot = sum(a*b for a,b in zip(mode, intent))
        norm_m = math.sqrt(sum(x*x for x in mode)) or 1e-6
        sim = dot / (norm_i * norm_m)
        att.append(max(0.0, sim))
    collective["attention"] = att

def feedback_intent_from_gmf(bead_chain, collective, gmf):
    if len(bead_chain) % 5 != 0:
        return
    traces = gmf["attractor_traces"]
    if not traces:
        return
    traces_sorted = sorted(traces, key=lambda x: x[2], reverse=True)
    strong_mode = traces_sorted[0][1]
    strength = CONFIG["attention"]["intent_feedback_strength"]
    collective["intent"] = [
        (1-strength)*a + strength*b for a,b in zip(collective["intent"], strong_mode)
    ]

# ================================================================
# 5. DIAGNOSTIC REPORT
# ================================================================
def diagnostic_report(tick, bead_chain, A, collective, warp_count, L, F, d):
    if not CONFIG["diagnostics"]["verbose"] or not bead_chain:
        return

    last_bead = bead_chain[-1]
    kernel = last_bead["kernel"]
    comp = last_bead["compression"]
    vol = kernel["volume"]
    edge_count = sum(sum(row) for row in A) // 2
    payload = last_bead["payload"]
    beads_cnt = len(payload.get("beads", []))
    highways_cnt = len(payload.get("highways", []))
    resonances_cnt = len(payload.get("resonances", []))
    gates_cnt = len(payload.get("gates", []))

    last_comp = kernel.get("last_comp", comp)
    stability = 1.0 / (1.0 + abs(comp - last_comp) + 0.01)

    index = (len(bead_chain) - 1) % len(d)
    last_mode = compute_mode_from_bead(last_bead, L, F, d, index)
    intent = collective["intent"]

    print(f"\n{'='*40}")
    print(f"DIAGNOSTIC @ tick {tick:4d}  | warps={warp_count}")
    print(f"Volume:       {vol:>8.4f}")
    crit_flag = "🔥 CRITICAL" if bead_is_critical(comp) else ""
    print(f"Compression:  {comp:>8.4f} {crit_flag}")
    print(f"Edges:        {edge_count:>8d} (nodes={len(A)})")
    print(f"Motifs:       beads={beads_cnt:2d} highways={highways_cnt:2d} "
          f"res={resonances_cnt:2d} gates={gates_cnt:2d}")
    print(f"Mode:         {[f'{x:.3f}' for x in last_mode]}")
    print(f"Intent:       {[f'{x:.3f}' for x in intent]}")
    print(f"Stability:    {stability:.4f}")
    print(f"{'='*40}\n")

    kernel["last_comp"] = comp

    if CONFIG["diagnostics"]["log_to_gmf"]:
        entry = {
            "tick": tick,
            "volume": vol,
            "compression": comp,
            "edges": edge_count,
            "beads": beads_cnt,
            "highways": highways_cnt,
            "resonances": resonances_cnt,
            "gates": gates_cnt,
            "stability": stability,
            "intent": intent[:],
            "mode": last_mode[:],
            "warp_count": warp_count,
        }
        gmf["diagnostics"].append(entry)

        # Attractor triggers
        cfg = CONFIG["diagnostics"]
        triggers = []
        if stability < cfg["attractor_trigger_stability"]:
            triggers.append("low_stability")
        if comp > cfg["attractor_trigger_compression"]:
            triggers.append("high_compression")

        if triggers:
            reason = "+".join(triggers)
            value = comp if "high_compression" in triggers else stability
            gmf["attractor_traces"].append((
                tick,
                last_mode[:],
                value,
                reason,
                edge_count
            ))
            if CONFIG["diagnostics"]["verbose"]:
                print(f"  → Attractor captured: {reason} (value={value:.3f})")

# ================================================================
# 6. MAIN TICK FUNCTION (simplified version for testing)
# ================================================================
def tick(pi_digits, bead_chain, A, collective, gmf, warp_count):
    L, F, T, Z, d = init_sim_pack(pi_digits)
    N = len(d)

    # Beads
    beads = []
    μF = sum(F) / N
    σF = (sum((x - μF)**2 for x in F) / N)**0.5
    thresh = CONFIG["motifs"]["bead_threshold_sigma"]
    for i in range(N-1):
        if F[i] > μF + thresh * σF:
            direction = 1 if d[i+1] > d[i] else -1
            j = max(0, min(N-1, i + direction))
            beads.append({"i": i, "j": j, "F_i": F[i]})

    # Highways, resonances, gates, etc. — simplified/stubbed for brevity in this test block
    highways = []
    resonances = []
    gates = []

    payload = {
        "beads": beads,
        "highways": highways,
        "resonances": resonances,
        "gates": gates
    }

    prev_bead = bead_chain[-1]
    new_kernel = evolve_kernel(prev_bead["kernel"], len(beads), beads, highways, resonances, gates)
    topo_sig = topology_hash(A)
    new_bead = make_bead(payload, topo_sig, new_kernel)

    # Warp if critical
    delta_edges = 0
    if bead_is_critical(new_bead["compression"]):
        node_index = (len(bead_chain) - 1) % len(A)
        A, delta = warp_rewire(A, node_index, new_bead["compression"])
        delta_edges = delta
        warp_count += 1
        if CONFIG["diagnostics"]["verbose"]:
            print(f"  WARP! delta edges = {delta:+d}")

    bead_chain.append(new_bead)

    # Mode & attention (simplified)
    MODES = [compute_mode_from_bead(b, L, F, d, i % N) for i, b in enumerate(bead_chain)]
    update_attention(collective, MODES)
    feedback_intent_from_gmf(bead_chain, collective, gmf)

    # Diagnostics
    if len(bead_chain) % CONFIG["diagnostics"]["log_interval"] == 0:
        diagnostic_report(
            len(bead_chain), bead_chain, A, collective, warp_count, L, F, d
        )

    return bead_chain, A, collective, gmf, warp_count

# ================================================================
# 7. RUN THE SIMULATION (test entry point)
# ================================================================
if __name__ == "__main__":
    print("Starting FTL π-Resonator Test Run...\n")

    pi_digits = get_pi_digits(CONFIG["pi"]["pi_length"])
    N_nodes = 20
    A, W = init_topology(N_nodes)  # W not used in this version
    bead_chain = [make_bead({}, topology_hash(A), make_kernel_state())]
    collective = init_collective_state()
    gmf = init_gmf()
    warp_count = 0

    TOTAL_TICKS = 300  # change as needed

    for t in range(1, TOTAL_TICKS + 1):
        bead_chain, A, collective, gmf, warp_count = tick(
            pi_digits, bead_chain, A, collective, gmf, warp_count
        )
        if t % 100 == 0:
            print(f"→ Completed tick {t} | warps={warp_count} | beads={len(bead_chain)}")

    print("\nSimulation finished.")
    print(f"Final compression: {bead_chain[-1]['compression']:.4f}")
    print(f"Final volume:      {bead_chain[-1]['kernel']['volume']:.4f}")
    print(f"Total warps:       {warp_count}")
    print(f"Stored diagnostics: {len(gmf['diagnostics'])} entries")
    print(f"Stored attractors:  {len(gmf['attractor_traces'])} events")
