---
name: stock
version: 1.0
description: |
  使用akshare库提供全面的股票数据查询功能，包括主营介绍、资金流向、涨停股池、板块异动、财经新闻等。
allowed-tools:
  - Read
  - Write
  - RunCommand
  - AskUserQuestion
---

# 股票数据查询技能

本技能通过调用 `akshare` 库，提供中国A股市场的多种股票数据查询功能。

## 功能

### 股票基础信息
- 主营介绍

### 资金流向
- 沪深港通资金流向
- 个股资金流
- 个股资金流排名
- 概念资金流
- 行业资金流
- 大盘资金流
- 大单追踪

### 涨停股池
- 涨停股池
- 强势股池
- 炸板股池

### 市场动态
- 板块异动
- 财经新闻
- 赚钱效应分析

## 参数传递格式

脚本支持以下三种参数传递方式：

1. **`--key value` 格式**（推荐）
   ```bash
   python scripts/akshare_stock_data.py stock_zt_pool_em --date 20260615
   ```

2. **`-key value` 格式**
   ```bash
   python scripts/akshare_stock_data.py stock_zt_pool_em -date 20260615
   ```

3. **`key=value` 格式**
   ```bash
   python scripts/akshare_stock_data.py stock_zt_pool_em date=20260615
   ```

## 工具定义

### stock_zyjs_ths

**一句话描述:** 获取指定股票的主营业务介绍
python路径：E:\Program Files\miniconda\envs\default_env\python.exe
**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_zyjs_ths`

**参数:**

| 名称     | 类型   | 描述                 | 是否必须 |
|----------|--------|----------------------|----------|
| `symbol` | string | 股票代码（如：000001） | true     |

---

### stock_hsgt_fund_flow_summary_em

**一句话描述:** 获取沪深港通资金流向汇总数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_hsgt_fund_flow_summary_em`

**参数:** 无

---

### stock_news_main_cx

**一句话描述:** 获取财经内容精选新闻

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_news_main_cx`

**参数:** 无

---

### stock_board_change_em

**一句话描述:** 获取当日板块异动详情

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_board_change_em`

**参数:** 无

---

### stock_zt_pool_em

**一句话描述:** 获取指定日期的涨停股池数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_zt_pool_em`

**参数:**

| 名称   | 类型   | 描述                     | 是否必须 |
|--------|--------|--------------------------|----------|
| `date` | string | 日期，格式：YYYYMMDD（如：20241008） | true     |

---

### stock_zt_pool_strong_em

**一句话描述:** 获取指定日期的强势股池数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_zt_pool_strong_em`

**参数:**

| 名称   | 类型   | 描述                     | 是否必须 |
|--------|--------|--------------------------|----------|
| `date` | string | 日期，格式：YYYYMMDD | true     |

---

### stock_zt_pool_zbgc_em

**一句话描述:** 获取指定日期的炸板股池数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_zt_pool_zbgc_em`

**参数:**

| 名称   | 类型   | 描述                     | 是否必须 |
|--------|--------|--------------------------|----------|
| `date` | string | 日期，格式：YYYYMMDD | true     |

---

### stock_market_activity_legu

**一句话描述:** 获取市场赚钱效应分析数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_market_activity_legu`

**参数:** 无

---

### stock_fund_flow_individual

**一句话描述:** 获取个股资金流数据（即时）

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_fund_flow_individual`

**参数:** 无

---

### stock_fund_flow_concept

**一句话描述:** 获取概念板块资金流数据（即时）

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_fund_flow_concept`

**参数:** 无

---

### stock_fund_flow_industry

**一句话描述:** 获取行业板块资金流数据（即时）

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_fund_flow_industry`

**参数:** 无

---

### stock_fund_flow_big_deal

**一句话描述:** 获取大单追踪数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_fund_flow_big_deal`

**参数:** 无

---

### stock_individual_fund_flow_rank

**一句话描述:** 获取个股资金流排名（今日）

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_individual_fund_flow_rank`

**参数:** 无

---

### stock_individual_fund_flow

**一句话描述:** 获取指定股票近100个交易日的资金流数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_individual_fund_flow`

**参数:**

| 名称     | 类型   | 描述                                          | 是否必须 |
|----------|--------|-----------------------------------------------|----------|
| `stock`  | string | 股票代码（如：000425）                          | true     |
| `market` | string | 市场代码：sh(上海)、sz(深圳)、bj(北京)           | true     |

---

### stock_market_fund_flow

**一句话描述:** 获取大盘资金流数据

**脚本:** `scripts/akshare_stock_data.py`
**函数:** `stock_market_fund_flow`

**参数:** 无
