# Build Order

[Flat Table Database](Flat%20Table%20Database%206f2c8b4e91d0a53f7c2e4b5a6d8f1c9e.csv)

## **Build Order (Bottom-Up)**

The `Build Order` column is the sequence. Read it as:

```
01–03  Clock + reset infrastructure          ← no logic dependencies
05–07  CPU tile: imem / dmem / CSR
10–11  CPU tile: L1 cache + MESI controller
25–30  Interconnect: L2 bank, directory, NIC
35    Interconnect: router
40    CPU subsystem
50    Interconnect subsystem (integration)
80–85  DMA tile
87–90  Perf counters
99    Integration: user_project_wrapper
```

**Rule:** a node's build number is always **higher than all its children**. That guarantees you never instantiate a module that doesn't exist yet.
