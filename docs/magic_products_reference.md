# Technical Reference: Magic Software Enterprises Product Suite (XPA, XPI, IMM)

**Document Ref**: MSE-TECH-REF-001  
**Author**: Antigravity Technical Systems Architect & Lead Engineer  
**Audience**: Support Operations, R&D Engineering, Integration Specialists  
**Status**: APPROVED / MASTER REFERENCE

---

## 1. Scope & Purpose

This document provides a detailed system architecture analysis of the installations discovered at `d:\XPA` and `d:\XPI` on this system. It outlines the core executables (`exe`), dynamic-link libraries (`dll`), Java archive configurations (`jar`), command scripts (`bat`), and initialization parameters (`ini`) that govern **Magic xpa**, **Magic xpi**, and the **In-Memory Middleware (IMM)**.

---

## 2. Magic xpa (Application Platform) Architecture

Magic xpa is a low-code metadata-driven application development and execution platform. The engine runs compiled cabinet files (`.ecf`) using a client/server or web client model.

### Key Directory Structures Analyzed (`d:\XPA`)
1. **Engine and Runtime Clients**:
   * `MgxpaStudio.exe`: Visual Studio-integrated development environment used to build application flows and metadata definitions.
   * `MgxpaRuntime.exe`: The primary client/server execution engine. Operates based on `MgxpaRuntime.exe.config` XML settings.
   * `MgBroker.exe`: Magic Request Broker. Manages client connections, load balances requests, and dynamically starts runtime engine sessions.
   * `MgBrokerMonitor.exe`: Graphical utility for tracking active broker servers, engines, and request queues.
2. **Database and Interface Adapters (DLLs)**:
   * `Btrieve14Adapter.dll` & `Btrieve15Adapter.dll`: Gateway adapters for Pervasive SQL/Btrieve databases.
   * `MGVAR.ocx` & `MG_OCX.dll`: ActiveX and Ole Control extension handlers.
   * `MGWSDLParser.dll`: SOAP web services parser.
   * `MGPVCSCom.dll` & `MGVSSCom.dll`: Version control adapters for PVCS and Microsoft Visual SourceSafe.
3. **Configurations (`.ini` & `.FRE`)**:
   * `MOD.ini` / `Magic.ini`: Core configurations.
     * `StartApplication`: Points to the startup cab (e.g. `d:\XPA\MailTest.ecf`).
     * `DefaultDatabase`: Typically configured for memory tables or SQLite/MSSQL.
     * `InternetDispatcherPath`: Maps requests to the internet gateway (e.g., `http://localhost/MagicScripts4111/MGrqispi.dll`).
     * `ConstFile`: Translates engine messages (e.g. French `SUPPORT\mgconstw.FRE` or Hebrew `Support\mgconstw.heb`).
4. **Log Formats (`mgerror.log`)**:
   * Thread-prefixed timestamp lines: `<ThreadID> DD/MM/YYYY HH:MM:SS.fff [Level] - Message`.
   * Standard error signatures include:
     * `This session was closed by the server(-197)`.
     * `Unknown Database, Data Source: [DB_Name]`.

---

## 3. Magic xpi (Integration Platform) Architecture

Magic xpi is an enterprise-grade integration platform designed to coordinate data flows between distinct business systems (such as SAP, Salesforce, databases, and message queues).

### Key Directory Structures Analyzed (`d:\XPI`)
1. **Studio & Development Editor**:
   * `MgxpiStudio.exe`: Visual editor for configuring connectors, triggers, data mappers, and orchestration flows.
   * `sapjco3.dll`: SAP Java Connector library. Crucial for connecting XPI integration flows directly to SAP RFC/BAPI interfaces.
   * `sqljdbc_auth.dll`: Driver dependency for SQL Server integrated security.
   * `debug.log`: Records Chrome Embedded Framework (CEF) rendering warnings for the Studio UI.
2. **Runtime Engine**:
   * Uses configuration scripts (`Config.ini`, `IFS.ini`, `DBMS.ini`) to map database connection strings, JMS/AMQP queue parameters, and client keys.
   * Leverages XML namespaces to handle structural data formatting.

---

## 4. Magic IMM (In-Memory Middleware) & HA Clustering

Magic IMM is the high-availability clustering and caching layer that underlies modern Magic xpi environments, allowing multi-node load balancing, session replication, and failover management.

### Key Directory Structures Analyzed (`d:\XPI\XPI4141\InMemoryMiddleware`)
1. **Agent Coordination**:
   * `agent/imm-agent.exe`: The primary Grid Service Agent (GSA) that coordinates Gigaspaces containers.
   * Manages lookup services (GSM/GSC/LUS) and watches over JVM lifecycle bindings.
2. **Configuration Rules (`config/`)**:
   * `globalsettings.properties`: Contains clustering parameters.
     * `magicXPIconfigProcessParameters`: Passes INI configurations (`IFS.INI`, `DBMS.INI`), space names, locator groups, and locator IP lists.
     * `acquireTimeoutMillis` (e.g., `10000` ms) and `messagesWaitingThresholdMinutes` (e.g. `10` minutes) control middleware locks.
   * `logback.xml`: Java logging specifications mapping events to `imm-agent.log`.
3. **Log Signatures & Failover**:
   * Magic IMM utilizes **GigaSpaces IMDG** (In-Memory Data Grid) and **Jini Lookup Services** (`LookupLocatorDiscovery`).
   * Standard errors include:
     * `SocketTimeoutException`: Lookup locator connect timed out.
     * `ConnectException`: Connection refused (LUS port offline).
     * `BindException` (Address already in use): Reggie lookup service failed to bind to TCP ports.
     * `SAException`: Storage adapter persistence failures during initial load syncs.
