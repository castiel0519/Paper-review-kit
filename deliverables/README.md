# 交付说明：机器学习与人工智能在微流控中的应用

## 交付物
| 文件 | 说明 |
|---|---|
| `机器学习与人工智能在微流控中的应用_读书报告.docx` | 精读读书报告（中文为主，英文题名保留；21篇 × 十大维度精读 + 横向对比 + 范式总结） |
| `机器学习与人工智能在微流控中的应用_研究报告.pptx` | 研究报告 PPT（16:9，共 50 页；每篇论文 2 页：内容讲解+Scheme ／ 研究范式+框架解析；另含封面/目录/背景/领域全景/横向对比/范式趋势/结论/参考文献） |
| `preview/幻灯片1~50.PNG` | PPT 导出预览图（供快速浏览与视觉留档） |
| `../papers/*.pdf` | 已下载的论文 PDF（20 篇中的 16 篇） |
| `../papers_txt/`, `../papers_figs/`, `../summaries/`, `../digests/` | 全文文本、Scheme 图、结构化精读摘要与精读缓冲 |
| `../check_report.json`, `../layout_report.json` | 自检报告 |

## 选文（21 篇，2020–2026）
覆盖 8 类场景：数字微流控；液滴/细胞图像识别与分类；液滴/细胞分选与实时控制；
实验设计与参数优化（逆设计/LLM/数字孪生）；器官芯片/生物传感/药物筛选；
疾病诊断与 POCT（CTC/外泌体/纸基微流控）；单细胞分析与高通量成像；综述与范式。

期刊涵盖 Nature Communications、Microsystems & Nanoengineering、Lab on a Chip、
Advanced Science、ACS Omega、ACS Sensors、Small、Matter、Physics of Fluids、
Digital Discovery、Micromachines、Acta Pharmaceutica Sinica B、npj Biosensing、
Frontiers in Bioengineering and Biotechnology、Scientific Reports、Advanced Photonics Research。

## 全文获取情况
- 已获取 PDF 全文并精读（16 篇）：01, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 14, 15, 19, 20, 21
  （来源：Nature/Springer、Europe PMC、Frontiers、Wiley（Repos）、MDPI/PMC、ACS/PMC、Radboud 仓库、d-nb 等）
- 出版方拦截 PDF、改用 Europe PMC 全文 XML 精读（1 篇）：02
- 未能获取全文、基于公开摘要与题录精读（4 篇）：13, 16, 17, 18
  （期刊闭源或网络/验证限制；报告摘要已按论文摘要与公开信息整理）

## 精读方法
- 检索核验：OpenAlex + Crossref + Europe PMC + Unpaywall/Semantic Scholar + 出版社官网。
- 下载：OA 直链优先（Europe PMC render 加速），依用户授权对个别闭源论文尝试第三方渠道；
  Sci-Hub 镜像在本次网络环境中不可达（DNS/自签名证书），未能补充获取。
- 精读隔离：本环境无 subagent 工具，采用「每篇独立文本文件 + 定向关键词检索 + 独立摘要文件」
  的隔离方式（等价于任务分发—并行读取—汇总），避免全文冗余占用主上下文。
- 报告/PPT 由统一结构化摘要（`summaries/summary_XX.json`）程序化生成，保证一致性。

## 自检结果
- `check_report.json`：PDF 魔数/页数校验通过；summary 必填字段完整；DOCX 可打开
  （755 段 / 44 表 / 16 图片）；PPTX 可打开（50 页 / 16 张图）。
- `layout_report.json`：50 页、1066 个文本框，无明显溢出风险。
- 视觉预览已导出为 PNG（`preview/`）；本会话模型不支持图像输入，无法由我人工目检，
  已通过结构自检与导出成功进行替代验证。
