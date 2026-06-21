<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Architecture

CMAR is a deterministic pipeline of independent streams chained so each output feeds the next. Modules in `src/cmar/`: scan, normalizer, quantizer, voids, plan, repair, autofill, protocol, integrator, falsifier, ledger, doctor, cli, model.
