# Passport Core Miniscript wallet-policy progress

Tracking issue: [SFT-974](https://linear.app/foundation-devices/issue/SFT-974/featured-add-support-for-miniscript)

Private development repository: <https://github.com/Foundation-Devices/passport2-miniscript>

## Objective

Add descriptor-backed Miniscript wallet policies to Passport Core so a user can
register a policy from a coordinator such as Liana, verify its spending rules
and addresses on Passport, and sign only PSBT inputs that match the registered
policy exactly.

This is implemented as core wallet-policy functionality, not as an extension.
The existing `MultisigWallet` implementation remains the compatibility path for
conventional M-of-N wallets. Miniscript policies may contain multisig fragments,
but may also contain timelocks, alternatives, thresholds, conditional branches,
and Taproot paths that cannot be represented by one global M/N value.

## Implemented

- Bounded, original Miniscript parser, type analysis, validation, and compiler
  for the accepted P2WSH and Taproot profiles.
- Checksummed descriptor and BIP388-style policy-template import.
- QR and microSD policy transport.
- Exact ownership proof by comparing the descriptor xpub with the xpub derived
  from the seed currently loaded on Passport.
- Network, key-origin, derivation-depth, duplicate-key, resource, and policy-ID
  validation.
- Registered policy storage with corruption quarantine and settings headroom.
- Address derivation and address verification through the shared wallet-policy
  interface.
- Exact P2WSH and Taproot PSBT matching with immutable per-input spend plans.
- Policy-derived verification of P2WSH change when a coordinator supplies the
  complete output derivations but omits `PSBT_OUT_WITNESS_SCRIPT`.
- Fail-closed separation between legacy multisig and registered policy inputs.
- Human-readable policy review derived only from the validated AST.
- Bounded rendering for complex AND, OR, threshold, multisig, timelock,
  conditional, and Taproot policies.
- Liana-style inheritance explanation with immediate and delayed spending states.
- Locally confirmed signer names that do not alter the descriptor or policy ID
  and are never accepted as coordinator-supplied semantic descriptions.
- Adaptive relative-locktime descriptions from one block through the BIP68
  maximum, time-based BIP68 units, and UTC dates for absolute timelocks.
- Explicit rejection of reserved or misleading BIP68 encodings.
- Clear mainnet/testnet mismatch diagnostics before ownership discovery.
- Policy-specific authorization review immediately before transaction signing.
- Sentence-case, progressive policy review that explains who can spend, when
  each path becomes available, the exact lock value, and which key is Passport's.
- Stable wallet-policy headers with the full user-supplied wallet name rendered
  in wrapping page content instead of a scrolling, easily clipped title.
- Post-registration actions for address verification, policy backup, signer
  labels, and opt-in technical details.
- Dedicated Connect Wallet export for Liana. It writes the minimal raw BIP48
  native-SegWit descriptor key that Liana accepts directly from a file. The
  same export works for single-key and multisig policy branches because the
  signature threshold belongs to the completed policy, not to the xpub.
- The Liana exporter is loaded only when selected, preserving the constrained
  startup heap.
- Coordinator-oriented PSBT errors with raw parser diagnostics on a second page.
- Explicit post-signing handoff instructions that distinguish Passport adding a
  signature from the wallet coordinator finalizing and broadcasting.
- Migration-safe loading of policy records created before signer names existed.

## Security invariants

- Coordinator prose is never trusted to explain a policy. Every displayed rule
  is derived from the parsed and validated descriptor tree.
- A policy must contain exactly one extended key proven to belong to the current
  Passport seed and exactly one Passport signing expression per input.
- The complete serialized xpub is compared; fingerprint equality is insufficient.
- Descriptor checksum and canonical policy identity are validated on import.
- A PSBT must match a registered policy's complete derived script, derivations,
  network, branch, address index, and supported sighash rules.
- Unknown policy scripts, ambiguous matches, mixed policies, and mixed legacy
  multisig/policy inputs fail closed.
- Taproot key-path bypasses and paths that do not require Passport are surfaced
  explicitly in the review UI.
- Relative timelocks cannot exceed the BIP68 encoding limits. A per-coin delay of
  1.5 years cannot be represented by one `older()` condition; longer calendar
  schedules require a different construction such as an absolute `after()`.

## User-flow decisions

- Keep `Multisig` and `Wallet Policies` separate in the current menu because the
  legacy multisig UI and import contract assume one global M-of-N rule.
- A future navigation cleanup should place both beneath a common customer-facing
  `Wallet Configurations` parent while retaining their separate validation paths.
- Use `wallet policy` in customer-facing backup language. Reserve `descriptor`
  for technical details and interoperable export internals.
- Show fingerprints as the durable comparison value and local signer names as
  user-confirmed labels.

## Hardware validation completed

- Developer-signed Color firmware boots on physical Passport Core hardware.
- Liana Testnet policy import succeeds from the coordinator-generated descriptor.
- Passport ownership is proven against the current seed.
- Policy registration succeeds and survives navigation/reboot.
- Liana and Passport derive and verify matching receive addresses.
- Human-readable immediate and delayed policy screens render on device.
- A Liana signing PSBT was captured after Passport rejected its P2WSH change
  output for a missing output witness script. Independent descriptor derivation
  proved that output branch `1`, index `1` exactly matches the registered policy.
  Passport now reconstructs that output script from the stored policy while
  continuing to require witness scripts for inputs and legacy multisig outputs.
- Firmware `v2.4.0b4` was built by GitHub Actions, signed with the throwaway
  developer key installed on the test device, independently signature-verified,
  and installed successfully.
- Firmware `v2.4.0b5` was built from private commit `6c79b4c0`, signed with the
  same throwaway developer key, independently verified, and copied to the test
  microSD. It installed successfully and signed the captured Liana Testnet PSBT
  on physical hardware.
- Firmware `v2.4.0b6` was built from private commit `422dd691`, signed with the
  same throwaway developer key, independently verified, and copied to the test
  microSD. Physical installation and the consolidated UX review are pending.

The `v2.4.0b4` signed-file SHA-256 is
`9042211f7205871ad00def4a9eee66c4f9f95ff523e2b764bbbd38bf87059145`.
The unsigned CI payload SHA-256 is
`860f19cf822f014dbb0df840c39498f4d75b91f878de64868a0c3ef4cf57b0c7`.

## Automated validation completed

- 106 Passport wallet-policy host tests pass.
- Regression coverage confirms a registered policy accepts an omitted output
  witness script only when the complete derivation map and scriptPubKey still
  match the independently derived policy output.
- Changed firmware modules compile with `mpy-cross`.
- Python formatting, REUSE, Rust formatting, Rust checks, and Rust tests pass.
- GitHub Actions successfully builds Color and Mono firmware, both simulators,
  both bootloaders, and host tools.
- Successful CI runs:
  - Build: <https://github.com/Foundation-Devices/passport2/actions/runs/31396457979>
  - Lint/test: <https://github.com/Foundation-Devices/passport2/actions/runs/31396457903>
  - Private `v2.4.0b5` build:
    <https://github.com/Foundation-Devices/passport2-miniscript/actions/runs/31403355734>
  - Private `v2.4.0b6` full build:
    <https://github.com/Foundation-Devices/passport2-miniscript/actions/runs/31408823982>
  - Private `v2.4.0b7` full build:
    <https://github.com/Foundation-Devices/passport2-miniscript/actions/runs/31473377450>
  - Private `v2.4.0b7` lint/test:
    <https://github.com/Foundation-Devices/passport2-miniscript/actions/runs/31473377426>

## Source checkpoints

- `c4c10e30` — registered Miniscript wallet-policy implementation.
- `0eba4aa4` — first semantic policy-review UI.
- `b6a82959` — adaptive timelines, signer names, network diagnostics, and
  policy-aware signing review. This is the source used for `v2.4.0b4`.
- `c2f52e1f` — wording improvements requested during physical-device review.
- `6c79b4c0` — policy-derived verification for Liana P2WSH change outputs that
  omit `PSBT_OUT_WITNESS_SCRIPT`. This is the source used for `v2.4.0b5`.
- `55f209fe` — calmer, sentence-case signing authorization language after the
  successful physical signing test.
- `422dd691` — consolidated wallet-policy registration, review, signing, error,
  and coordinator-handoff UX. This is the source used for `v2.4.0b6`.
- `1b483c5e` — fixes policy address verification without an active account,
  freezes the post-signing display module, and top-aligns long registration
  confirmations. This is the source used for `v2.4.0b7`.

## Pending physical and product validation

- Install and review the consolidated post-signing and registration UX candidate
  after its source and automated checks are complete.
- Return the device-signed PSBT to Liana, confirm Liana accepts and finalizes it,
  and record the resulting Testnet transaction ID if it is broadcast.
- Exercise representative complex policies, including threshold multisig,
  multiple alternate paths, time-based relative locks, absolute locks, and
  Taproot script paths.
- Validate the dedicated Liana key file with both single-key and multisig setup
  templates, then register and verify each completed policy on Passport.
- Test policy export, backup, restore, rename, signer-label migration, deletion,
  and re-registration on physical hardware.
- Test malformed, oversized, wrong-network, wrong-seed, duplicate-key, ambiguous,
  and adversarial policy/PSBT inputs on the device.
- Decide the final information architecture for standard multisig and wallet
  policies before customer release.
- Complete security review, firmware-size review, translation/copy review, and
  coordinator interoperability testing beyond Liana.

## Sensitive and non-source artifacts

The throwaway firmware-signing private key, developer-key bundle, signed firmware
binaries, recovery firmware, and microSD contents are deliberately excluded from
Git. Their local evidence directory is
`/Users/admin/Documents/ChatGPT/passport-miniscript-signing.jDMtXv` on the test
machine. Do not copy that directory into this repository.

The captured Liana PSBT is also excluded from Git. Its local evidence copy is
`/Users/admin/Documents/ChatGPT/passport-miniscript-psbt-evidence/liana-signing-failure.psbt`
with SHA-256
`3ebe771cd7d1e9bfce9d422e49d4d5ae6b345837301e18712c750b15778ee546`.

The `v2.4.0b5` unsigned CI payload SHA-256 is
`d1bee2d609ef1cd37827003146beabfe5689d9d1aeb9a136934d35b82924d6bc`.
The signed-file SHA-256 is
`7599c870415dfcc2c6975e496d9155fa35560f5a41e12ea39348ed8c26cd660d`.

The `v2.4.0b6` unsigned CI payload SHA-256 is
`2fc95d98d72b85408f34fb600cc5f9b91f2ff6be3a9bfd132cda9df8b0cdc695`.
The signed-file SHA-256 is
`136e98783333f19c5ec5234046db2c5d978adb6bcd7675cf7a6f7a4e3f3e4ed7`.
