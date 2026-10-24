"""
corpus.py —— 正常文本语料库
===========================
用于建立 token/char 比值的基线分布。

设计原则：
    必须覆盖「正常但 token/char 比值高」的合法情况，
    否则阈值定不出来（会把正常文本误判为攻击）。

    高风险合法类别：
      - emoji（多字节，token 膨胀）
      - 稀有语言（阿拉伯语、泰语、印地语）
      - 特殊符号（数学、货币、箭头）
      - 代码（符号密集）
      - JSON（标点密集）
"""
import json
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CORPUS = {
    "zh_tech": [
        "本文介绍了一种基于马尔可夫链的序列预测方法，用于分析智能体工具调用序列的结构可预测性。实验表明，二阶马尔可夫模型在留出集上的 top-1 准确率达到百分之四十五点六七。",
        "漏洞响应平台的核心流程包括注册、身份认证、漏洞提交、平台初审、厂商复审和奖励发放六个环节。其中厂商复审环节的耗时直接影响白帽子的收益周期。",
        "工业控制系统普遍采用 PLC 与 SCADA 架构，Modbus 协议在设计之初未考虑认证机制，导致攻击者可在未授权情况下读取寄存器数据并修改控制参数。",
        "深度学习模型的训练过程需要大量标注数据，而数据标注的质量直接决定模型性能上限。在安全领域，标注数据的稀缺性是制约检测模型泛化能力的主要瓶颈。",
        "网络流量分析通常依赖 NetFlow 或 IPFIX 协议采集元数据，通过对流记录的统计分析可以识别端口扫描、数据外传和命令控制信道的周期性特征。",
        "静态代码审计工具通过抽象语法树和污点传播分析来追踪不可信输入，但面对动态语言和反射调用时，其召回率会显著下降，需要人工复核来降低误报。",
        "分布式系统的可观测性依赖指标、日志和链路追踪三大支柱，其中链路追踪通过传播上下文标识符来还原跨服务的调用路径，是定位性能瓶颈的关键手段。",
        "密码学协议的安全性证明通常基于归约方法，将攻击者攻破协议的能力归约为解决某个公认困难问题，例如离散对数或大整数分解。",
        "容器编排平台通过声明式配置管理应用生命周期，其安全边界取决于命名空间隔离、网络策略和准入控制器的正确配置，任一环节疏漏都可能导致横向移动。",
        "模糊测试通过变异输入样本来触发目标程序的异常行为，覆盖率引导的灰盒模糊测试在发现内存安全漏洞方面效果显著，但对需要特定状态序列的逻辑漏洞效果有限。",
        "零信任架构的核心理念是不信任任何默认网络位置，每次访问请求都需要经过身份验证和授权决策，这要求细粒度的策略引擎和持续的信任评估机制。",
        "软件供应链攻击通过在构建或分发环节植入恶意代码来影响下游用户，防御需要覆盖依赖成分分析、构建环境加固和制品签名验证三个层面。",
        "应急响应流程通常遵循准备、识别、遏制、根除、恢复和经验总结六个阶段，其中遏制阶段的关键决策是隔离范围与业务连续性的权衡。",
        "威胁情报的共享依赖标准化的数据格式，STIX 用于描述威胁对象及其关系，TAXII 则定义了传输协议，二者共同构成自动化情报交换的基础。",
        "侧信道攻击通过观测密码学实现的时间、功耗或电磁辐射特征来推断密钥，防御手段包括常数时间实现、掩码技术和随机化调度。",
        "云原生安全的核心挑战在于边界模糊化，传统的网络边界防护模型不再适用，需要转向基于身份和工作负载的细粒度访问控制。",
        "二进制漏洞利用通常需要绕过地址空间布局随机化和数据执行保护，信息泄露漏洞在此过程中起到关键作用，可用来获取内存布局和代码基址。",
        "数据脱敏在保留数据可用性的同时消除敏感信息，常用方法包括掩码、泛化、置换和差分隐私，选择取决于下游分析任务对数据精度的要求。",
        "安全编排自动化与响应平台通过剧本将重复的响应动作标准化，显著缩短平均响应时间，但剧本的维护成本和误触发风险需要持续投入。",
        "协议逆向工程通过分析网络流量中的字段边界和状态转换来推断私有协议的语义，常用技术包括报文聚类、字段边界识别和状态机学习。",
        "访问控制模型经历了从自主访问控制到强制访问控制再到基于角色的访问控制，近年基于属性的访问控制因其表达能力和上下文感知而广泛应用。",
        "日志分析的核心难点在于信噪比，真实环境中百分之九十以上的告警是误报，需要通过基线建模、关联分析和白名单机制来压缩告警数量。",
        "内存取证通过分析物理内存镜像来恢复运行时的进程、网络连接和注入代码，Volatility 框架提供了跨平台的插件体系来支持不同操作系统的分析。",
        "威胁狩猎是一种主动的安全防御方法，假设攻击者已经存在于网络中，通过构建假设、验证假设和迭代优化来发现传统检测手段遗漏的痕迹。",
        "代码签名机制通过数字证书验证软件来源和完整性，但证书泄露和签名滥用使得该机制并非绝对可靠，需要结合信誉系统和行为分析。",
        "蜜罐技术通过部署诱饵系统来吸引和观测攻击者行为，其价值在于低成本获取真实攻击样本和攻击者基础设施信息。",
        "安全多方计算允许多方在不泄露各自输入的前提下共同计算函数结果，其性能瓶颈主要在于通信开销和电路规模。",
        "同态加密支持在密文上直接进行运算，全同态加密虽然理论完备但性能开销巨大，实际应用多采用部分同态加密方案。",
        "网络协议栈的实现缺陷往往源于边界条件处理不当，例如长度字段与实际缓冲区大小不一致导致越界写入，这类问题在嵌入式系统中尤为常见。",
        "威胁建模在系统设计阶段识别潜在的安全风险，常用方法包括 STRIDE 分类、攻击树分析和数据流图标注，其产出是后续安全测试的输入。",
    ],
    "en_tech": [
        "The vulnerability arises from a race condition in the session validation logic, where the authentication check and the resource access occur in separate transactions without proper locking.",
        "Static analysis tools often produce false positives when dealing with dynamic dispatch, because the call graph cannot be resolved precisely at compile time.",
        "Fuzzing campaigns benefit significantly from seed corpus quality; a well-chosen initial input set can reduce time to first crash by an order of magnitude.",
        "The threat model assumes an attacker with local network access but no valid credentials, which is consistent with the assumed-breach scenario described in the engagement scope.",
        "Container escape techniques typically exploit misconfigured volume mounts or privileged capabilities, allowing the attacker to reach the host kernel namespace.",
        "Differential privacy provides a formal guarantee that the output distribution changes only marginally when a single record is added or removed from the dataset.",
        "The exploit chains an information disclosure to defeat address space layout randomization, then leverages a use-after-free to achieve arbitrary code execution.",
        "Incident response playbooks should be version controlled and regularly exercised, otherwise they tend to drift out of sync with the actual environment.",
        "Supply chain attacks increasingly target the build pipeline rather than the source code, because the pipeline has access to signing keys and deployment credentials.",
        "The detection rule correlates authentication failures with subsequent privilege escalation attempts within a five minute window, reducing alert fatigue significantly.",
        "Kernel level rootkits modify system call tables or hook internal structures to hide their presence from user space monitoring tools.",
        "The protocol lacks forward secrecy, meaning that compromise of the long term key retroactively decrypts all previously recorded sessions.",
        "Threat intelligence feeds vary widely in quality; without normalization and scoring, ingestion pipelines quickly become overwhelmed by low fidelity indicators.",
        "The sandbox uses seccomp filters to restrict the syscall surface, but the filter policy must be carefully audited because an overly permissive rule defeats the isolation.",
        "Memory safety violations remain the dominant root cause of critical vulnerabilities in C and C++ codebases, despite decades of tooling improvements.",
        "The access control model follows the principle of least privilege, granting each service account only the permissions required for its specific function.",
        "Side channel leakage through timing variations can be mitigated by constant time implementations, though this often imposes a measurable performance penalty.",
        "The forensic timeline correlates file system metadata, registry artifacts, and event logs to reconstruct attacker activity across the intrusion lifecycle.",
        "Credential stuffing attacks exploit password reuse across services, and rate limiting alone is insufficient without breached credential detection.",
        "The vulnerability disclosure process balances transparency against the risk of exploitation, typically allowing a ninety day window before public disclosure.",
        "Zero trust architecture replaces implicit network trust with continuous verification of identity, device posture, and contextual risk signals.",
        "The exploit primitive is a heap overflow that corrupts an adjacent object pointer, granting a write-what-where condition under attacker control.",
        "Log ingestion at scale requires sampling and aggregation strategies, otherwise storage costs grow faster than the analytical value derived from the data.",
        "The threat actor demonstrates operational security discipline, rotating infrastructure frequently and avoiding reusable malware artifacts across campaigns.",
        "Cryptographic agility is the ability to migrate to new algorithms without disrupting deployed systems, increasingly important as quantum computing advances.",
        "The vulnerability scanner produces a high volume of informational findings that obscure the few critical issues requiring immediate remediation.",
        "Security orchestration platforms automate repetitive triage tasks, but the automation logic itself becomes an attack surface if not properly hardened.",
        "The attack surface analysis enumerates externally reachable services and maps each to the corresponding authentication and authorization controls.",
        "Data exfiltration detection relies on establishing baseline egress volume per host, then flagging statistically significant deviations from that baseline.",
        "The patch management process prioritizes vulnerabilities by exploitability and business impact rather than by raw CVSS score alone.",
    ],
    "mixed": [
        "本文使用 OWASP ZAP 进行被动扫描，通过 Burp Suite 的 Repeater 模块手工验证，最终确认了 SQL Injection 漏洞，CVSS 评分 9.8。",
        "在 Kubernetes 集群中，RBAC 配置错误是最常见的提权路径，攻击者可通过 create pods 权限挂载 hostPath 来逃逸到宿主机。",
        "使用 tiktoken 的 cl100k_base 编码器统计 token 数量，发现 Tag 字符载体导致 token 膨胀达到 13.2 倍，而字符数保持不变。",
        "该 CVE 影响 Apache Log4j 2.x 版本，攻击者通过 JNDI lookup 触发远程类加载，进而实现 Remote Code Execution。",
        "在 Windows 环境下，通过 Get-WmiObject 查询 Win32_Process 可以枚举进程命令行，但需要相应的 WMI 权限。",
        "使用 Playwright 驱动 Chromium 进行页面渲染，通过 page.evaluate 执行 JavaScript 来提取 DOM 文本和计算样式。",
        "Redis 未授权访问漏洞的利用链通常包括写入 SSH 公钥、写入 crontab 任务或写入 webshell 三种方式。",
        "在 Linux 下使用 auditd 记录系统调用，通过 ausearch 和 aureport 工具分析审计日志，可以还原攻击者的操作序列。",
        "使用 Volatility 3 的 windows.pslist 插件枚举进程，通过 windows.malfind 检测注入的内存区域。",
        "该 SQL 注入点位于 id 参数，通过 UNION SELECT 可以回显数据库版本和表结构，进而 dump 用户凭据表。",
        "在 AWS 环境中，IAM 角色权限过大是常见的配置风险，攻击者可通过 AssumeRole 链式提权到管理员权限。",
        "使用 Nuclei 模板批量检测常见漏洞，通过 -severity critical 参数过滤高危结果，减少人工复核工作量。",
        "该 XSS 漏洞位于搜索框，通过构造 img onerror 事件可以执行任意 JavaScript，窃取用户 Cookie。",
        "在 Docker 容器中，如果挂载了 docker.sock，攻击者可以直接控制宿主机上的 Docker daemon，实现容器逃逸。",
        "使用 tcpdump 抓包后用 Wireshark 分析，发现攻击者使用了 DNS 隧道进行数据外传，单次查询携带 200 字节载荷。",
        "该 SSRF 漏洞可访问云厂商的元数据服务，获取临时凭证后接管整个云账号。",
        "在 Python 中，pickle 反序列化漏洞可导致任意代码执行，攻击者构造恶意 pickle 数据即可在 load 时触发。",
        "使用 semgrep 进行静态扫描，通过自定义规则检测硬编码密钥，规则匹配到 12 处疑似问题。",
        "该 JWT 实现未校验签名算法，攻击者可将 alg 改为 none 绕过验证，伪造任意用户身份。",
        "在 Nginx 配置中，alias 路径遍历漏洞可导致任意文件读取，通过 ../ 序列可以读取 /etc/passwd。",
        "使用 Shodan 搜索暴露的工控设备，通过 port 502 可以定位 Modbus 服务，进一步探测设备型号和固件版本。",
        "该 OAuth 实现存在 redirect_uri 校验不严的问题，攻击者可将授权码劫持到自己的服务器。",
        "在 Java 应用中，Fastjson 反序列化漏洞影响广泛，通过 autoType 特性可以加载任意类。",
        "使用 Burp Collaborator 检测盲注和 SSRF，通过 DNS 回连确认漏洞存在性。",
        "该文件上传功能仅校验 Content-Type，攻击者可修改请求头绕过，上传 webshell 获取服务器权限。",
        "在 Spring Boot Actuator 中，如果暴露了 env 端点，攻击者可以读取环境变量中的数据库密码和密钥。",
        "使用 Ghidra 反编译二进制文件，通过交叉引用定位关键校验函数，patch 后绕过授权检查。",
        "该 CORS 配置允许任意源，配合 credentials 为 true 时，攻击者可跨域读取受害者敏感数据。",
        "在 MongoDB 中，未授权访问可导致全库数据泄露，默认配置下 27017 端口对外暴露是常见问题。",
        "使用 BloodHound 分析 Active Directory 攻击路径，通过 ACL 关系可以发现从普通用户到域管的提权链。",
    ],
    "short": [
        "PHP 紧急补丁发布",
        "漏洞利用量达数百万次",
        "新型勒索软件活跃",
        "供应链攻击溯源分析",
        "零信任架构落地实践",
        "大模型提示词注入防御",
        "工控协议安全研究",
        "内存取证技术解析",
        "威胁情报共享标准",
        "容器逃逸手法汇总",
        "身份认证绕过技巧",
        "云原生安全基线",
        "代码审计方法论",
        "应急响应流程规范",
        "红蓝对抗实战复盘",
        "漏洞赏金平台对比",
        "安全运营中心建设",
        "密码学协议分析",
        "逆向工程入门指南",
        "日志分析最佳实践",
        "网络流量异常检测",
        "恶意样本行为分析",
        "访问控制模型演进",
        "数据脱敏技术选型",
        "模糊测试框架评测",
        "静态分析工具对比",
        "动态插桩技术实践",
        "符号执行应用场景",
        "协议逆向工程方法",
        "侧信道攻击防御",
    ],
    "code": [
        "def parse_config(path: str) -> dict:\n    with open(path, 'r', encoding='utf-8') as f:\n        return json.load(f)",
        "for i in range(len(items)):\n    if items[i].get('status') == 'active':\n        result.append(items[i]['id'])",
        "try:\n    conn = sqlite3.connect(db_path)\n    cursor.execute(query, params)\nexcept sqlite3.Error as e:\n    logger.error(f'db error: {e}')",
        "class Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        self.send_response(200)\n        self.end_headers()\n        self.wfile.write(b'ok')",
        "const result = data.filter(x => x.score > 0.5).map(x => ({ id: x.id, name: x.name }));",
        "SELECT u.id, u.name, COUNT(o.id) AS cnt\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id\nGROUP BY u.id, u.name\nHAVING cnt > 5;",
        "async function fetchData(url) {\n  const resp = await fetch(url);\n  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);\n  return resp.json();\n}",
        "import numpy as np\narr = np.random.randn(1000, 1000)\nresult = np.linalg.inv(arr @ arr.T)",
        "if __name__ == '__main__':\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--input', required=True)\n    args = parser.parse_args()",
        "<div class=\"container\">\n  <h1>{{ title }}</h1>\n  <ul>\n    {% for item in items %}<li>{{ item.name }}</li>{% endfor %}\n  </ul>\n</div>",
        "git log --oneline --graph --all --decorate | head -20",
        "docker run -d --name app -p 8080:80 -v $(pwd)/data:/data nginx:latest",
        "curl -X POST https://api.example.com/v1/chat -H 'Content-Type: application/json' -d '{\"model\":\"gpt-4\",\"messages\":[]}'",
        "kubectl get pods -n production -o wide --sort-by=.metadata.creationTimestamp",
        "find /var/log -name '*.log' -mtime -7 -exec grep -l 'ERROR' {} \\;",
        "awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10",
        "ps aux | grep -E 'nginx|apache' | grep -v grep | awk '{print $2}' | xargs kill -9",
        "tcpdump -i eth0 -n 'tcp port 443' -w capture.pcap -c 1000",
        "nmap -sS -sV -p- --min-rate 1000 -oA scan 192.168.1.0/24",
        "sqlmap -u 'http://target/page?id=1' --batch --level 3 --risk 2 --dbs",
    ],
    "json_data": [
        '{"id": 1, "name": "test", "status": "active", "created_at": "2026-10-24T10:00:00Z"}',
        '{"error": {"code": 401, "message": "Unauthorized", "details": {"reason": "token expired"}}}',
        '[{"id": 1, "score": 0.95}, {"id": 2, "score": 0.87}, {"id": 3, "score": 0.72}]',
        '{"users": [{"uid": "u001", "roles": ["admin", "user"], "active": true}]}',
        '{"config": {"timeout": 30, "retries": 3, "endpoints": ["a.example.com", "b.example.com"]}}',
        '{"meta": {"total": 1523, "page": 1, "per_page": 50}, "items": []}',
        '{"event": "login_failed", "src_ip": "192.168.1.100", "user": "admin", "ts": 1792800000}',
        '{"vulnerability": {"cve": "CVE-2026-12345", "cvss": 9.8, "affected": [">= 1.0", "< 2.3.1"]}}',
        '{"metrics": {"cpu": 45.2, "memory": 78.9, "disk_io": {"read": 1024, "write": 512}}}',
        '{"rules": [{"id": "R001", "severity": "high", "match": {"field": "user_agent", "regex": ".*sqlmap.*"}}]}',
        '{"trace": {"trace_id": "abc123", "spans": [{"span_id": "s1", "duration_ms": 45}]}}',
        '{"alert": {"type": "intrusion", "confidence": 0.88, "indicators": ["T1190", "T1059"]}}',
        '{"asset": {"hostname": "web-01", "ip": "10.0.1.15", "os": "Ubuntu 22.04", "services": [22, 80, 443]}}',
        '{"finding": {"title": "SQL Injection", "severity": "critical", "location": "/api/user?id=1"}}',
        '{"batch": [{"op": "insert", "table": "logs", "values": ["2026-10-24", "error", "timeout"]}]}',
        '{"policy": {"name": "least-privilege", "rules": [{"effect": "deny", "action": "*", "resource": "admin/*"}]}}',
        '{"scan": {"target": "example.com", "ports": [80, 443], "results": {"80": "open", "443": "open"}}}',
        '{"session": {"sid": "sess_abc", "user_id": 1024, "expires_in": 3600, "scope": ["read", "write"]}}',
        '{"report": {"generated": "2026-10-24", "total_findings": 27, "by_severity": {"critical": 2, "high": 5}}}',
        '{"payload": {"type": "poc", "target": "CVE-2026-6791", "verified": false, "notes": "pending validation"}}',
    ],
    "emoji": [
        "今天的会议讨论了三件事：🔒 安全加固、📊 数据合规、🚀 产品迭代。",
        "部署成功 ✅ 所有服务健康检查通过 🎉 可以下班了 😄",
        "⚠️ 注意：这个接口存在风险，建议先做测试再上线 🔍",
        "修复进度：🐛 已确认 → 🔧 修复中 → ✅ 已验证 → 📦 待发布",
        "团队协作工具：💬 沟通 → 📝 记录 → 📌 归档 → 🔔 提醒",
        "性能优化结果：内存 ⬇️ 30%，CPU ⬇️ 15%，响应时间 ⬇️ 40% 📈",
        "安全检查清单：🔐 权限 ✅ ｜ 🌐 网络 ✅ ｜ 💾 数据 ⏳ ｜ 📋 日志 ✅",
        "项目里程碑：🏁 需求评审完成 → 🚧 开发中 → 🧪 测试中 → 🎯 上线",
        "Bug 优先级：🔥 P0 立即修 ｜ ⚡ P1 本周修 ｜ 🕐 P2 排期修",
        "架构演进：单体 🏢 → 微服务 🧩 → 服务网格 🕸️ → Serverless ☁️",
        "数据流：采集 📥 → 清洗 🧹 → 存储 💾 → 分析 🔬 → 展示 📊",
        "告警等级：🔴 严重 ｜ 🟠 高危 ｜ 🟡 中危 ｜ 🟢 低危 ｜ 🔵 提示",
        "发布流程：代码合并 🔀 → 构建 🏗️ → 测试 🧪 → 灰度 🎨 → 全量 🌍",
        "监控面板：CPU 💻 45% ｜ 内存 🧠 78% ｜ 磁盘 💿 62% ｜ 网络 🌐 稳定",
        "事故复盘：🔍 定位问题 → 🛠️ 临时修复 → 🩹 根因修复 → 📖 更新文档",
        "任务状态：📋 待办 ｜ 🔄 进行中 ｜ 👀 评审中 ｜ ✅ 完成 ｜ ❌ 取消",
        "技术栈：前端 ⚛️ React ｜ 后端 🐍 Python ｜ 数据库 🐘 PostgreSQL",
        "安全防护：🛡️ WAF ｜ 🔥 防火墙 ｜ 🔑 密钥管理 ｜ 📜 审计日志",
        "自动化流程：触发 ⚡ → 执行 ⚙️ → 验证 🔍 → 通知 📬 → 归档 📁",
        "文档结构：📖 概述 ｜ 🔧 安装 ｜ 🚀 使用 ｜ ❓ 常见问题 ｜ 📞 联系",
    ],
    "special_symbols": [
        "计算公式：E = mc²，其中 c ≈ 3×10⁸ m/s，能量单位为焦耳（J）。",
        "价格：¥1,280.00 → ¥998.00（立减 ¥282，约 22% off）",
        "温度范围：-40°C ~ +85°C，湿度 5% ~ 95% RH（无凝露）",
        "流量统计：↑ 1.2 GB/s ｜ ↓ 3.4 GB/s ｜ 丢包率 0.02%",
        "数学表达式：∑(i=1 to n) i² = n(n+1)(2n+1)/6",
        "坐标：北纬 39°54′27″，东经 116°23′17″，海拔 43.5 m",
        "逻辑表达式：¬(A ∧ B) ≡ (¬A) ∨ (¬B)，这是德摩根定律。",
        "版本对比：v2.3.1 → v2.4.0，Δ = +12 features, −3 deprecated",
        "性能指标：P50 = 45ms ｜ P95 = 120ms ｜ P99 = 380ms ｜ P99.9 = 1.2s",
        "误差范围：测量值 3.14159 ± 0.00001（相对误差 3.2×10⁻⁶）",
        "时间格式：2026-10-24T17:42:47+08:00（ISO 8601 标准）",
        "货币换算：$1,000 USD ≈ ¥7,200 CNY（汇率 7.2）",
        "化学式：2H₂ + O₂ → 2H₂O（放热反应，ΔH = −572 kJ/mol）",
        "统计结果：均值 μ = 45.6，标准差 σ = 12.3，样本量 n = 1,024",
        "网络地址：192.168.1.0/24，可用主机数 254 个，网关 .1",
        "概率表示：P(A|B) = P(B|A)·P(A) / P(B)（贝叶斯定理）",
        "单位换算：1 GiB = 1,024 MiB = 1,048,576 KiB = 1,073,741,824 B",
        "区间表示：[0, 1) 表示左闭右开，(−∞, +∞) 表示全体实数。",
        "编码示例：Base64('hello') = 'aGVsbG8='，十六进制 0x68656C6C6F",
        "角度换算：90° = π/2 rad ≈ 1.5708 rad，360° = 2π rad",
    ],
    "multilang": [
        "本日は晴天なり。東京の気温は22度で、湿度は65パーセントです。",
        "오늘 회의에서 보안 정책 개정안을 논의했습니다. 다음 주까지 검토 의견을 제출해 주세요.",
        "Сегодня мы обсудили новые требования к безопасности информационных систем.",
        "تمت مناقشة خطة الاستجابة للحوادث في الاجتماع اليوم.",
        "วันนี้อากาศดีมาก อุณหภูมิ 28 องศาเซลเซียส",
        "आज की बैठक में सुरक्षा नीति पर चर्चा हुई।",
        "Hôm nay chúng ta sẽ thảo luận về chính sách bảo mật mới.",
        "วันนี้มีการประชุมเรื่องความปลอดภัยของระบบ",
        "Σήμερα συζητήσαμε τα νέα μέτρα ασφαλείας για τα πληροφοριακά συστήματα.",
        "היום דנו במדיניות האבטחה החדשה של הארגון.",
        "今日は会議でセキュリティポリシーの改訂について話し合いました。",
        "오늘은 보안 감사 결과를 검토하는 시간을 가졌습니다.",
        "Мы обсудили результаты аудита безопасности за прошлый квартал.",
        "ناقشنا اليوم نتائج تقييم المخاطر الأمنية للمنصة الجديدة.",
        "การประชุมวันนี้สรุปผลการทดสอบความปลอดภัยเรียบร้อยแล้ว",
        "आज हमने नई सुरक्षा नीति के बारे में विस्तार से बात की।",
        "Chúng tôi đã hoàn thành đánh giá bảo mật cho hệ thống mới tuần này.",
        "Σήμερα ολοκληρώσαμε την αξιολόγηση ασφαλείας του νέου συστήματος.",
        "השלמנו היום את הערכת האבטחה של המערכת החדשה.",
        "本日の会議では、新しいセキュリティ基準の適用範囲について確認しました。",
    ],
    "long_form": [
        "在分布式系统的可观测性建设中，指标、日志和链路追踪构成了三大支柱。指标提供聚合层面的趋势洞察，适合发现异常但难以定位根因；日志保留原始事件细节，是定位问题的关键证据但存储成本高；链路追踪通过上下文传播还原跨服务调用路径，能精确定位性能瓶颈。三者的协同使用需要统一的关联标识符，通常是一个全局唯一的 trace id，在请求入口处生成并贯穿整个调用链。工程实践中，采样策略的选择直接影响成本与效果的平衡：头部采样实现简单但会丢失长尾请求，尾部采样能保留异常但需要缓冲完整链路数据。此外，标签基数的控制是可观测性系统能否长期运行的关键约束，高基数标签会导致存储爆炸和查询性能急剧下降。",
        "应急响应流程通常遵循六个阶段：准备、识别、遏制、根除、恢复和经验总结。准备阶段的工作往往被低估，但实际决定了后续所有环节的效率上限，包括资产清单的准确性、联系方式的时效性、工具链的可用性和预案的演练频率。识别阶段的核心挑战是区分真实攻击与误报，需要结合多源证据进行交叉验证，单一告警源的置信度通常不足以支撑重大决策。遏制阶段涉及隔离范围与业务连续性的权衡，过度隔离会造成业务中断，隔离不足则可能让攻击者继续横向移动。根除阶段需要确保攻击者建立的所有持久化机制都被清除，遗漏任何一个都可能导致攻击者重新进入。恢复阶段应分阶段进行，先在受控环境中验证系统正常，再逐步放开流量。经验总结阶段的价值在于将本次事件中的发现转化为可复用的检测规则和流程改进。",
        "软件供应链安全的核心挑战在于信任传递的脆弱性。一个典型应用可能直接依赖数十个开源库，而这些库又各自依赖更多传递性依赖，形成一棵深度可达五到六层的依赖树。攻击者只需要在这棵树的任意节点植入恶意代码，就能影响所有下游使用者。防御需要覆盖多个层面：依赖成分分析用于识别已知漏洞的依赖版本，但无法发现尚未披露的恶意包；构建环境加固确保构建过程本身不被篡改，包括构建机的访问控制、构建脚本的完整性和构建产物的可重现性；制品签名验证提供了从构建到部署的端到端完整性保证，但前提是签名密钥本身的安全。近年来的实际攻击案例表明，攻击者更倾向于攻击构建和分发环节而非源代码仓库，因为这些环节通常有更高的权限和更弱的监控。",
        "内存安全漏洞仍然是 C 和 C++ 代码库中最主要的高危漏洞来源，尽管静态分析、模糊测试和运行时检测工具已经发展了数十年。根本原因在于这类语言将内存管理的责任交给了开发者，而人类在处理复杂的生命周期和边界条件时不可避免会出错。缓解措施分为三个层次：编译期检查通过更严格的类型系统和边界检查来在编译阶段发现问题，但受限于语言特性无法覆盖所有情况；运行时检测通过插桩和影子内存来捕获越界访问和使用后释放，代价是显著的性能开销，通常在两到三倍之间；硬件辅助方案利用 CPU 提供的内存标签或指针认证机制，性能开销较小但需要特定硬件支持。长期来看，向内存安全语言迁移是根本解决之道，但大规模代码库的迁移成本极高，更现实的路径是在新代码中采用安全语言，同时用缓解措施保护存量代码。",
        "威胁情报的共享面临质量和隐私的双重挑战。质量方面，不同来源的情报在准确性、时效性和粒度上差异巨大，缺乏标准化会导致下游系统被低质量指标淹没。实践中需要建立评分机制，综合考虑来源可信度、历史准确率、时效衰减和上下文相关性。隐私方面，原始情报往往包含受害者的敏感信息，例如被攻击的资产 IP、泄露的凭据片段和内部网络拓扑，共享前必须经过脱敏处理。STIX 和 TAXII 标准解决了格式和传输的问题，但没有解决信任和隐私的问题。近年出现的隐私保护情报共享方案尝试用差分隐私或安全多方计算来在共享威胁特征的同时保护个体隐私，但性能和可用性仍是主要障碍。",
        "零信任架构的落地难点不在于技术选型，而在于组织流程的改造。传统边界防护模型的隐含假设是内网可信，因此内部系统之间的访问控制往往非常宽松，这导致一旦攻击者突破边界就能横向移动。零信任要求对每次访问都进行身份验证和授权决策，这意味着原本隐式的信任关系必须被显式建模，需要梳理清楚每个服务对每个资源的访问需求。这个梳理工作的规模通常被严重低估：一个中等规模的企业可能有数千个服务实例和数万个访问关系。此外，持续信任评估需要采集设备状态、用户行为和上下文风险信号，这些数据的采集本身涉及隐私合规问题。",
        "密码学协议的安全性分析需要区分几个层次。首先是原语层面的安全性，例如分组密码的抗差分和线性密码分析能力、哈希函数的抗碰撞性，这些通常有严格的形式化定义和证明。其次是协议构造层面的安全性，需要通过归约证明来表明攻破协议等价于解决某个困难问题。第三是实现层面的安全性，即使协议在理论上是安全的，实现中的侧信道泄露、随机数生成缺陷或错误处理不当都可能导致实际被攻破。最后是部署层面的安全性，包括密钥管理、证书验证和协议版本协商，配置错误在真实世界造成的安全事件远多于密码学原语的破解。",
        "工业控制系统的安全防护与 IT 系统有本质区别。首先是可用性优先，工控系统通常要求 7×24 小时连续运行，任何可能导致停机的安全措施都需要慎重评估。其次是协议遗留问题，Modbus、DNP3 等协议设计于网络隔离时代，缺乏认证和加密机制，而替换这些协议需要更换大量现场设备，成本极高。第三是设备资源受限，许多 PLC 和 RTU 的计算能力和内存极其有限，无法运行复杂的安全代理。因此工控安全通常采用纵深防御策略：在网络层用工业防火墙做协议白名单，在主机层用白名单机制限制可执行程序，在管理层面建立严格的操作审计流程。",
        "数据脱敏的目标是在保护敏感信息的同时保留数据的分析价值，这两个目标存在内在张力。过度脱敏会导致数据失去分析意义，脱敏不足则存在泄露风险。常用方法各有适用场景：掩码保留格式但破坏语义，适合展示场景；泛化降低精度但保留分布特征，适合统计分析；置换保持字段间关联但打乱个体对应关系，适合关联分析；差分隐私通过添加噪声提供形式化保证，适合发布聚合统计结果。选择方法时需要明确下游分析任务的具体需求，例如如果分析需要精确的数值分布，泛化可能比掩码更合适。",
        "模糊测试的有效性高度依赖于种子语料的质量和变异策略的设计。覆盖率引导的灰盒模糊测试通过插桩获取代码覆盖率反馈，优先变异能产生新覆盖路径的输入，这在实际应用中效果显著。但对于需要特定状态序列才能触发的漏洞，例如需要先完成认证再访问特定资源的逻辑漏洞，纯粹的覆盖率引导效率很低，因为到达漏洞点需要满足一系列前置条件。针对这类问题，研究者提出了基于状态机的模糊测试和基于协议语法的模糊测试，通过显式建模状态转换和报文结构来生成更有效的测试用例。",
    ],
}


def get_corpus():
    """返回扁平的 (类别, 文本) 列表。"""
    items = []
    for cat, texts in CORPUS.items():
        for t in texts:
            items.append((cat, t))
    return items


def stats():
    items = get_corpus()
    print(f"语料总数: {len(items)}")
    print("\n分类统计:")
    for cat, texts in CORPUS.items():
        avg_len = sum(len(t) for t in texts) / len(texts)
        print(f"  {cat:18s} {len(texts):3d} 条, 平均 {avg_len:.0f} 字符")


if __name__ == "__main__":
    stats()
