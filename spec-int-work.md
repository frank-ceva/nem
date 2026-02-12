This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.


# Deferred device model extensions

These items were identified during the "Extend NEM device model for full NPM architectural coverage" initiative but deferred as separate future work items.

- **Fusion chain capability declaration:** Declaring what NMU->CSTL fusion paths a device supports. To be addressed as a separate work item.
- **DMA connectivity matrix:** Declaring which DMA instances connect to which memory paths. May be addressed together with fusion or separately.

---

# Common infrastructure
Before proceeding with the development of the NEM tools, we need to define the common infrastrcture that will be shared by all these tools, and develop it before we start working on the tools so that we avoid code duplication and redundancy.
Analyze the intent of the tools, and suggest what should be common across 2 or more of them.
