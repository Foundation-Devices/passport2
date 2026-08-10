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
- Firmware `v2.4.0b4` was built by GitHub Actions, signed with the throwaway
  developer key installed on the test device, independently signature-verified,
  and installed successfully.

The `v2.4.0b4` signed-file SHA-256 is
`9042211f7205871ad00def4a9eee66c4f9f95ff523e2b764bbbd38bf87059145`.
The unsigned CI payload SHA-256 is
`860f19cf822f014dbb0df840c39498f4d75b91f878de64868a0c3ef4cf57b0c7`.

## Automated validation completed

- 94 Passport wallet-policy host tests pass.
- Changed firmware modules compile with `mpy-cross`.
- Python formatting, REUSE, Rust formatting, Rust checks, and Rust tests pass.
- GitHub Actions successfully builds Color and Mono firmware, both simulators,
  both bootloaders, and host tools.
- Successful CI runs:
  - Build: <https://github.com/Foundation-Devices/passport2/actions/runs/31396457979>
  - Lint/test: <https://github.com/Foundation-Devices/passport2/actions/runs/31396457903>

## Source checkpoints

- `c4c10e30` — registered Miniscript wallet-policy implementation.
- `0eba4aa4` — first semantic policy-review UI.
- `b6a82959` — adaptive timelines, signer names, network diagnostics, and
  policy-aware signing review. This is the source used for `v2.4.0b4`.
- The next private checkpoint contains wording improvements requested during
  physical-device review and has intentionally not yet been built.

## Pending physical and product validation

- Finish the revised on-device wording review.
- Build and install the next candidate only after the wording pass is complete.
- Sign and finalize a real Liana Testnet PSBT; verify the policy authorization
  page appears immediately before final approval.
- Exercise representative complex policies, including threshold multisig,
  multiple alternate paths, time-based relative locks, absolute locks, and
  Taproot script paths.
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
