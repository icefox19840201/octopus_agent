import os
# 禁用AVX指令，解决CPU指令集不兼容问题
os.environ['OPENBLAS_NO_AVX2'] = '1'
os.environ['OPENBLAS_NO_AVX'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import akshare as ak
import json
def stock_zyjs_ths(symbol):
    '''
    主营介绍
    symbol:股票代码
    :return:
    '''
    stock_zyjs_ths_df = ak.stock_zyjs_ths(symbol=symbol)
    print(stock_zyjs_ths_df)
    return stock_zyjs_ths_df.to_json(orient='records')
def stock_hsgt_fund_flow_summary_em():
    '''
    沪深港通资金流向
    :return:
    '''
    stock_hsgt_fund_flow_summary_em_df = ak.stock_hsgt_fund_flow_summary_em()
    print(stock_hsgt_fund_flow_summary_em_df)
    return stock_hsgt_fund_flow_summary_em_df.to_json(orient='records')
def stock_news_main_cx():
    '''
    财经内容精选
    :return:
    '''
    stock_news_main_cx_df = ak.stock_news_main_cx()
    print(stock_news_main_cx_df)
    return stock_news_main_cx_df.to_json(orient='records')
def stock_board_change_em():
    '''
    当日板块异动详情
    :return:
    '''
    stock_board_change_em_df = ak.stock_board_change_em()
    print(stock_board_change_em_df)
    return stock_board_change_em_df.to_json(orient='records')
def stock_zt_pool_em(date):
    '''
    单次返回指定日期的涨停股池数据
    date格式：'20241008'
    :return:
    '''
    stock_zt_pool_em_df = ak.stock_zt_pool_em(date=date)
    print(stock_zt_pool_em_df)
    return stock_zt_pool_em_df.to_json(orient='records')
def stock_zt_pool_strong_em(date):
    '''
    获取强势股股票池
    :param date: 日期，格式：YYYYMMDD（如：20241231）
    :return:
    '''
    stock_zt_pool_strong_em_df = ak.stock_zt_pool_strong_em(date=date)
    print(stock_zt_pool_strong_em_df)
    return stock_zt_pool_strong_em_df.to_json(orient='records')
def stock_zt_pool_zbgc_em(date):
    '''
    炸板股票池
    date:日期，格式：'20241011'
    :return:
    '''
    stock_zt_pool_zbgc_em_df = ak.stock_zt_pool_zbgc_em(date=date)
    print(stock_zt_pool_zbgc_em_df)
    return stock_zt_pool_zbgc_em_df.to_json(orient='records')
def stock_market_activity_legu():
    '''
    赚钱效应分析
    :return:
    '''
    stock_market_activity_legu_df = ak.stock_market_activity_legu()
    print(stock_market_activity_legu_df)
    return stock_market_activity_legu_df.to_json(orient='records')
def stock_fund_flow_individual():
    '''
    个股资金流
    :return:
    '''
    stock_fund_flow_individual_df = ak.stock_fund_flow_individual(symbol="即时")
    print(stock_fund_flow_individual_df)
    return stock_fund_flow_individual_df.to_json(orient='records')
def stock_fund_flow_concept():
    '''
    概念资金流
    :return:
    '''
    stock_fund_flow_concept_df = ak.stock_fund_flow_concept(symbol="即时")
    print(stock_fund_flow_concept_df)
    return stock_fund_flow_concept_df.to_json(orient='records')
def stock_fund_flow_industry():
    '''
    行业资金流
    :return:
    '''
    stock_fund_flow_industry_df = ak.stock_fund_flow_industry(symbol="即时")
    print(stock_fund_flow_industry_df)
    return stock_fund_flow_industry_df.to_json(orient='records')
def stock_fund_flow_big_deal():
    '''
    单次获取当前时点的所有大单追踪数据
    :return:
    '''
    stock_fund_flow_big_deal_df = ak.stock_fund_flow_big_deal()
    print(stock_fund_flow_big_deal_df)
    return stock_fund_flow_big_deal_df.to_json(orient='records')
def stock_individual_fund_flow_rank():
    '''
    个股资金流排名
    :return:
    '''
    stock_individual_fund_flow_rank_df = ak.stock_individual_fund_flow_rank(indicator="今日")
    print(stock_individual_fund_flow_rank_df)
    return stock_individual_fund_flow_rank_df.to_json(orient='records')
def stock_individual_fund_flow(stock,market):
    '''
    单次获取指定市场和股票的近 100 个交易日的资金流数据
    :param stock:stock="000425"; 股票代码
    :param market:market="sh"; 上海证券交易所: sh, 深证证券交易所: sz, 北京证券交易所: bj
    :return:
    '''
    stock_individual_fund_flow_df = ak.stock_individual_fund_flow(stock=stock, market=market)
    print(stock_individual_fund_flow_df)
    return stock_individual_fund_flow_df.to_json(orient='records')
def stock_market_fund_flow():
    '''
    获取大盘资金流
    :return:
    '''
    stock_market_fund_flow_df = ak.stock_market_fund_flow()
    print(stock_market_fund_flow_df)
    return stock_market_fund_flow_df.to_json(orient='records')
def stock_zt_pool_dtgc_em(date):
    '''
    跌停股池
    date:日期，格式：'20241011'
    :return:
    '''
    stock_zt_pool_dtgc_em_df = ak.stock_zt_pool_dtgc_em(date=date)
    print(stock_zt_pool_dtgc_em_df)
    return stock_zt_pool_dtgc_em_df.to_json(orient='records')
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        func_name = sys.argv[1]
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            # 支持 --key value 格式
            if arg.startswith('--'):
                key = arg[2:]  # 去掉 --
                if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                    value = sys.argv[i + 1]
                    i += 2
                else:
                    value = True  # 布尔标志
                    i += 1
                kwargs[key] = value
            # 支持 -key value 格式
            elif arg.startswith('-') and len(arg) > 1:
                key = arg[1:]  # 去掉 -
                if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                    value = sys.argv[i + 1]
                    i += 2
                else:
                    value = True
                    i += 1
                kwargs[key] = value
            # 支持 key=value 格式
            elif '=' in arg:
                k, v = arg.split('=', 1)
                kwargs[k] = v
                i += 1
            else:
                i += 1
        
        if func_name == 'stock_zt_pool_em':
            result = stock_zt_pool_em(**kwargs)
        elif func_name == 'stock_zt_pool_strong_em':
            result = stock_zt_pool_strong_em(**kwargs)
        elif func_name == 'stock_zt_pool_zbgc_em':
            result = stock_zt_pool_zbgc_em(**kwargs)
        elif func_name == 'stock_market_fund_flow':
            result = stock_market_fund_flow()
        elif func_name == 'stock_fund_flow_industry':
            result = stock_fund_flow_industry()
        elif func_name == 'stock_fund_flow_concept':
            result = stock_fund_flow_concept()
        elif func_name == 'stock_individual_fund_flow_rank':
            result = stock_individual_fund_flow_rank()
        elif func_name == 'stock_market_activity_legu':
            result = stock_market_activity_legu()
        elif func_name == 'stock_board_change_em':
            result = stock_board_change_em()
        elif func_name == 'stock_fund_flow_individual':
            result = stock_fund_flow_individual()
        elif func_name == 'stock_fund_flow_big_deal':
            result = stock_fund_flow_big_deal()
        elif func_name == 'stock_hsgt_fund_flow_summary_em':
            result = stock_hsgt_fund_flow_summary_em()
        elif func_name == 'stock_news_main_cx':
            result = stock_news_main_cx()
        elif func_name == 'stock_zyjs_ths':
            result = stock_zyjs_ths(**kwargs)
        elif func_name == 'stock_individual_fund_flow':
            result = stock_individual_fund_flow(**kwargs)
        elif func_name == 'stock_zt_pool_dtgc_em':
            result = stock_zt_pool_dtgc_em(**kwargs)
        else:
            print(f"Unknown function: {func_name}")
            sys.exit(1)
        print(f"\n---JSON_START---\n{result}\n---JSON_END---")
    else:
        stock_zt_pool_em('20260526')
