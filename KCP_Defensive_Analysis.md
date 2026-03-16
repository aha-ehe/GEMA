# Defensive Analysis of KCP Implementation in libmoba.so

## 1. Overview
This document explores the network reliability protocol (KCP) implemented within `libmoba.so`. Based on static analysis of the binary, it highlights theoretical vulnerabilities related to client-side manipulation of KCP parameters (`ikcp_nodelay` and `ikcp_wndsize`). If a client modifies these parameters beyond reasonable limits, it could potentially induce resource exhaustion (lag or Denial of Service) on the centralized game server handling the match lobby.

**The goal of this analysis is to demonstrate the importance of server-side validation for all incoming client configurations and traffic patterns.**

## 2. Identified Vulnerability Vector: Parameter Manipulation
KCP is a highly configurable, low-latency ARQ protocol. Its aggressiveness and throughput are controlled by parameters set during initialization (typically on the client side before connecting).

In `libmoba.so`, the initialization occurs within a function wrapping the KCP library:
`_ZN3mfw11ReliableUdp4initERKNS0_10KcpOptionsE` (approx offset `0x000cae34`)

Inside this initialization block, arguments for core configuration functions (`ikcp_wndsize` and `ikcp_nodelay`) are loaded from memory/structs and passed via registers `W1`, `W2`, `W3`, `W4` prior to execution via a Branch with Link (`BL`) instruction.

### Theoretical Attack:
A malicious actor could theoretically modify the `libmoba.so` binary (e.g., via hex-patching or inline hooking) to overwrite the loaded configuration values with extreme extremes.

1.  **Window Size Manipulation (`ikcp_wndsize`):** By forcing the maximum *send window* (`snd_wnd`) to its absolute maximum limit (e.g., `0xFFFF`), the client disables its own congestion control mechanism, allowing an unlimited number of unacknowledged packets to flood the network toward the server.
2.  **NoDelay Manipulation (`ikcp_nodelay`):** By modifying the arguments passed to this function (e.g., setting `interval` to 0, `nodelay` to 1, `resend` to an aggressive value, and forcing the `nc` (Net Congestion) flag to 0), the client operates in an ultra-aggressive state, instantly transmitting packets without any throttling.

### The Impact (Server Exhaustion):
If the centralized server processing the UDP packets for a specific game room does not enforce strict limits (Rate Limiting) on incoming throughput or packet frequency per client, this flood of packets will overwhelm the server's CPU or bandwidth capacity allocated for that room. Consequently, all other legitimate players connected to the same room will experience severe latency (lag) or packet loss due to the server struggling to process the flood from the modified client.

---

## 3. Mitigation Strategies (Defensive Engineering)

To secure the game server against such client-side manipulations, the following mitigations **must** be implemented on the server-side infrastructure:

### A. Strict Server-Side Validation & Overrides
Never trust the parameters provided or requested by the client. The server must dictate the maximum allowable `snd_wnd` (send window), `rcv_wnd` (receive window), and MTU sizes.
*   **Action:** When initializing the KCP session on the server, ensure that the server-side limits are hard-capped. If a client attempts to negotiate or send data exceeding a reasonable threshold (e.g., window size > 128), the server should either clamp the value or disconnect the client immediately.

### B. Implementation of Per-Client Rate Limiting (Throttling)
Even if a modified client bypasses its own KCP congestion control, the server must act as the ultimate gatekeeper.
*   **Action:** Implement a Token Bucket or Leaky Bucket algorithm at the application layer (or UDP socket layer) to monitor the incoming packet rate and byte rate per client connection.
*   **Thresholds:** Define a maximum acceptable packet per second (PPS) and bandwidth limit based on the game's actual data requirements (e.g., a 5v5 MOBA rarely needs more than 30-60 updates per second per client).
*   **Enforcement:** If a client exceeds the defined threshold significantly, the server should drop the excess packets (simulate loss to force the client to back off, though a malicious client won't care) or proactively terminate the connection (Kick/Ban) for anomalous behavior.

### C. Sanity Checks on Packet Structure
Beyond the rate of packets, the server must validate the *content* and structure. As observed during the initial reverse engineering phase, the `libmoba.so` implementation also incorporates a custom `lib7zip` compression wrapper (`KCP_EnableZip`).
*   **Action:** Ensure the server has robust error handling and resource limits for the decompression routine. A flood of malformed compressed packets (Zip Bombs) could cause CPU spikes or memory exhaustion. Set maximum decompressed size limits and timeouts for processing individual packets.

## 4. Conclusion
Relying on client-side constraints (like unmodified binaries or obfuscation) for network stability is a flawed security model. Modifying the assembly of `libmoba.so` to induce a network flood is technically feasible and relatively straightforward for an attacker using tools like radare2. The only effective defense is a robust, zero-trust server architecture that strictly enforces rate limits, validates KCP parameters, and quickly disconnects anomalous clients to protect the integrity of the match for all other players.