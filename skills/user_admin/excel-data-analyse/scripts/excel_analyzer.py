#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel数据分析脚本
基于pandas和openpyxl实现
支持数据清洗、统计分析、数据透视表等功能
返回ECharts图表JSON数据供前端渲染
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import json

import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class ExcelAnalyzer:
    """Excel数据分析器"""

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.df = None
        self.original_df = None
        self._load_data()

    def _load_data(self):
        """加载Excel数据"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        try:
            # 尝试读取所有sheet
            xls = pd.ExcelFile(self.file_path)
            if len(xls.sheet_names) > 1:
                print(f"检测到多个工作表: {xls.sheet_names}")
                print(f"默认使用第一个工作表: {xls.sheet_names[0]}")

            self.df = pd.read_excel(self.file_path)
            self.original_df = self.df.copy()
            print(f"成功加载数据: {len(self.df)} 行 x {len(self.df.columns)} 列")
        except Exception as e:
            raise Exception(f"读取Excel文件失败: {str(e)}")

    def info(self):
        """显示数据基本信息"""
        print("\n" + "="*60)
        print("数据基本信息")
        print("="*60)
        print(f"文件路径: {self.file_path}")
        print(f"数据维度: {self.df.shape[0]} 行 x {self.df.shape[1]} 列")
        print(f"\n列名:")
        for i, col in enumerate(self.df.columns, 1):
            print(f"  {i}. {col}")

        print(f"\n数据类型:")
        print(self.df.dtypes)

        print(f"\n缺失值统计:")
        missing = self.df.isnull().sum()
        if missing.sum() == 0:
            print("  无缺失值")
        else:
            for col in missing[missing > 0].index:
                print(f"  {col}: {missing[col]} 个缺失值 ({missing[col]/len(self.df)*100:.1f}%)")

        print(f"\n重复行数: {self.df.duplicated().sum()}")
        print("="*60)

    def stats(self, columns=None):
        """描述性统计分析"""
        print("\n" + "="*60)
        print("描述性统计分析")
        print("="*60)

        if columns:
            cols = [c.strip() for c in columns.split(',')]
            numeric_df = self.df[cols].select_dtypes(include=[np.number])
        else:
            numeric_df = self.df.select_dtypes(include=[np.number])

        if numeric_df.empty:
            print("没有数值型列可供分析")
            return

        stats = numeric_df.describe()
        print("\n基本统计量:")
        print(stats.round(2))

        # 额外的统计信息
        print("\n额外统计信息:")
        extra_stats = pd.DataFrame({
            '偏度': numeric_df.skew(),
            '峰度': numeric_df.kurtosis(),
            '变异系数': numeric_df.std() / numeric_df.mean()
        }).round(2)
        print(extra_stats)

        print("="*60)
        return stats

    def clean(self, output_path, drop_duplicates=True, fill_missing=None):
        """数据清洗"""
        print("\n" + "="*60)
        print("数据清洗")
        print("="*60)

        df_clean = self.df.copy()
        original_rows = len(df_clean)

        # 删除重复行
        if drop_duplicates:
            dup_count = df_clean.duplicated().sum()
            if dup_count > 0:
                df_clean = df_clean.drop_duplicates()
                print(f"删除重复行: {dup_count} 行")
            else:
                print("无重复行")

        # 处理缺失值
        missing_before = df_clean.isnull().sum().sum()
        if missing_before > 0:
            if fill_missing == 'mean':
                for col in df_clean.select_dtypes(include=[np.number]).columns:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].mean())
                print("使用均值填充数值型缺失值")
            elif fill_missing == 'median':
                for col in df_clean.select_dtypes(include=[np.number]).columns:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].median())
                print("使用中位数填充数值型缺失值")
            elif fill_missing == 'mode':
                for col in df_clean.columns:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].mode()[0])
                print("使用众数填充缺失值")
            elif fill_missing == 'drop':
                df_clean = df_clean.dropna()
                print("删除包含缺失值的行")
            else:
                print(f"发现 {missing_before} 个缺失值，未处理")
        else:
            print("无缺失值")

        # 保存清洗后的数据
        df_clean.to_excel(output_path, index=False)
        print(f"\n清洗完成!")
        print(f"原始数据: {original_rows} 行")
        print(f"清洗后: {len(df_clean)} 行")
        print(f"输出文件: {output_path}")
        print("="*60)

        return df_clean

    def pivot(self, index, values, aggfunc='sum', columns=None, output_path=None):
        """生成数据透视表"""
        print("\n" + "="*60)
        print("数据透视表")
        print("="*60)

        try:
            pivot_params = {
                'index': index,
                'values': values,
                'aggfunc': aggfunc
            }
            if columns:
                pivot_params['columns'] = columns

            pivot_table = pd.pivot_table(self.df, **pivot_params)
            print(f"\n透视表结果:")
            print(pivot_table)

            if output_path:
                pivot_table.to_excel(output_path)
                print(f"\n透视表已保存: {output_path}")

            print("="*60)
            return pivot_table
        except Exception as e:
            print(f"生成透视表失败: {str(e)}")
            return None

    def _generate_echarts_option(self, chart_type, x_col, y_col, title=None):
        """生成ECharts图表配置"""
        try:
            # 准备数据
            x_data = self.df[x_col].astype(str).tolist()
            y_data = self.df[y_col].tolist()

            # 根据图表类型生成配置
            if chart_type == 'bar':
                option = {
                    "title": {"text": title or f"{y_col} by {x_col}", "left": "center"},
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {"type": "category", "data": x_data, "axisLabel": {"rotate": 45}},
                    "yAxis": {"type": "value"},
                    "series": [{"data": y_data, "type": "bar"}]
                }
            elif chart_type == 'line':
                option = {
                    "title": {"text": title or f"{y_col} by {x_col}", "left": "center"},
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
                    "yAxis": {"type": "value"},
                    "series": [{"data": y_data, "type": "line", "smooth": True}]
                }
            elif chart_type == 'pie':
                pie_data = [{"name": str(x), "value": y} for x, y in zip(x_data, y_data)]
                option = {
                    "title": {"text": title or f"{y_col} by {x_col}", "left": "center"},
                    "tooltip": {"trigger": "item"},
                    "series": [{
                        "type": "pie",
                        "radius": "50%",
                        "data": pie_data
                    }]
                }
            elif chart_type == 'scatter':
                scatter_data = [[x, y] for x, y in zip(x_data, y_data)]
                option = {
                    "title": {"text": title or f"{y_col} vs {x_col}", "left": "center"},
                    "tooltip": {"trigger": "item"},
                    "xAxis": {"type": "category", "data": list(set(x_data))},
                    "yAxis": {"type": "value"},
                    "series": [{"data": scatter_data, "type": "scatter"}]
                }
            else:
                return None

            return option
        except Exception as e:
            print(f"生成ECharts配置失败: {str(e)}")
            return None

    def chart(self, chart_type, x, y, title=None):
        """生成图表，返回ECharts配置"""
        print("\n" + "="*60)
        print(f"生成图表: {chart_type}")
        print("="*60)

        try:
            option = self._generate_echarts_option(chart_type, x, y, title)
            if option:
                # 输出ECharts标记和数据
                print("\n---ECHARTS_START---")
                print(json.dumps(option, ensure_ascii=False, indent=2))
                print("---ECHARTS_END---\n")
                print("="*60)
                return option
            else:
                print(f"不支持的图表类型: {chart_type}")
                return None
        except Exception as e:
            print(f"生成图表失败: {str(e)}")
            return None

    def correlation(self, columns=None):
        """相关性分析，返回ECharts热力图配置"""
        print("\n" + "="*60)
        print("相关性分析")
        print("="*60)

        if columns:
            cols = [c.strip() for c in columns.split(',')]
            numeric_df = self.df[cols].select_dtypes(include=[np.number])
        else:
            numeric_df = self.df.select_dtypes(include=[np.number])

        if numeric_df.empty or len(numeric_df.columns) < 2:
            print("需要至少两列数值型数据进行相关性分析")
            return None

        corr_matrix = numeric_df.corr()
        print("\n相关系数矩阵:")
        print(corr_matrix.round(2))

        # 生成ECharts热力图配置
        try:
            columns_list = corr_matrix.columns.tolist()
            data = []
            for i, col1 in enumerate(columns_list):
                for j, col2 in enumerate(columns_list):
                    data.append([j, i, round(corr_matrix.loc[col1, col2], 2)])

            option = {
                "title": {"text": "相关性热力图", "left": "center"},
                "tooltip": {"position": "top"},
                "grid": {"height": "50%", "top": "10%"},
                "xAxis": {"type": "category", "data": columns_list, "splitArea": {"show": True}},
                "yAxis": {"type": "category", "data": columns_list, "splitArea": {"show": True}},
                "visualMap": {
                    "min": -1,
                    "max": 1,
                    "calculable": True,
                    "orient": "horizontal",
                    "left": "center",
                    "bottom": "15%",
                    "inRange": {"color": ["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"]}
                },
                "series": [{
                    "type": "heatmap",
                    "data": data,
                    "label": {"show": True}
                }]
            }

            print("\n---ECHARTS_START---")
            print(json.dumps(option, ensure_ascii=False, indent=2))
            print("---ECHARTS_END---\n")
            print("="*60)
        except Exception as e:
            print(f"生成热力图失败: {str(e)}")

        return corr_matrix

    def trend(self, date_col, value_col, freq='M'):
        """时间序列趋势分析，返回ECharts配置"""
        print("\n" + "="*60)
        print("时间序列趋势分析")
        print("="*60)

        try:
            # 转换日期列
            self.df[date_col] = pd.to_datetime(self.df[date_col])

            # 设置日期索引
            df_ts = self.df.set_index(date_col)

            # 重采样
            if freq == 'D':
                resampled = df_ts[value_col].resample('D').sum()
                freq_name = '日'
            elif freq == 'W':
                resampled = df_ts[value_col].resample('W').sum()
                freq_name = '周'
            elif freq == 'M':
                resampled = df_ts[value_col].resample('M').sum()
                freq_name = '月'
            elif freq == 'Q':
                resampled = df_ts[value_col].resample('Q').sum()
                freq_name = '季度'
            else:
                resampled = df_ts[value_col].resample('M').sum()
                freq_name = '月'

            print(f"\n{freq_name}度统计:")
            print(resampled.describe())

            # 生成ECharts配置
            x_data = resampled.index.astype(str).tolist()
            y_data = resampled.values.tolist()

            option = {
                "title": {"text": f'{value_col} {freq_name}度趋势', "left": "center"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
                "yAxis": {"type": "value"},
                "series": [{"data": y_data, "type": "line", "smooth": True, "areaStyle": {}}]
            }

            print("\n---ECHARTS_START---")
            print(json.dumps(option, ensure_ascii=False, indent=2))
            print("---ECHARTS_END---\n")
            print("="*60)

            return resampled
        except Exception as e:
            print(f"趋势分析失败: {str(e)}")
            return None

    def full_report(self, output_dir):
        """生成完整分析报告"""
        print("\n" + "="*60)
        print("生成完整分析报告")
        print("="*60)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_dir / f"analysis_report_{timestamp}.md"

        # 生成报告内容
        report_lines = []
        report_lines.append("# Excel数据分析报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"\n源文件: {self.file_path}")
        report_lines.append(f"\n## 1. 数据概览")
        report_lines.append(f"\n- 数据维度: {self.df.shape[0]} 行 x {self.df.shape[1]} 列")
        report_lines.append(f"- 列名: {', '.join(self.df.columns)}")

        # 数据类型
        report_lines.append(f"\n## 2. 数据类型")
        report_lines.append("")
        report_lines.append("| 列名 | 数据类型 |")
        report_lines.append("|------|----------|")
        for col, dtype in self.df.dtypes.items():
            report_lines.append(f"| {col} | {dtype} |")

        # 缺失值
        report_lines.append(f"\n## 3. 数据质量")
        missing = self.df.isnull().sum()
        report_lines.append(f"\n- 重复行数: {self.df.duplicated().sum()}")
        report_lines.append(f"- 缺失值总数: {missing.sum()}")
        if missing.sum() > 0:
            report_lines.append("")
            report_lines.append("| 列名 | 缺失值数量 | 缺失比例 |")
            report_lines.append("|------|------------|----------|")
            for col in missing[missing > 0].index:
                pct = missing[col] / len(self.df) * 100
                report_lines.append(f"| {col} | {missing[col]} | {pct:.1f}% |")

        # 数值型统计
        numeric_df = self.df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            report_lines.append(f"\n## 4. 描述性统计")
            report_lines.append("")
            report_lines.append(numeric_df.describe().round(2).to_markdown())

        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        # 保存清洗后的数据
        clean_file = output_dir / f"cleaned_data_{timestamp}.xlsx"
        self.df.to_excel(clean_file, index=False)

        print(f"\n报告已生成:")
        print(f"  - 分析报告: {report_file}")
        print(f"  - 清洗数据: {clean_file}")
        print("="*60)

        return report_file


def main():
    parser = argparse.ArgumentParser(description='Excel数据分析工具')
    parser.add_argument('command', choices=['info', 'stats', 'clean', 'pivot', 'chart', 'correlation', 'trend', 'full'],
                       help='分析命令')
    parser.add_argument('--file', '-f', required=True, help='Excel文件路径')
    parser.add_argument('--output', '-o', help='输出路径')
    parser.add_argument('--columns', '-c', help='指定列（逗号分隔）')
    parser.add_argument('--index', '-i', help='透视表行字段')
    parser.add_argument('--values', '-v', help='透视表值字段')
    parser.add_argument('--aggfunc', '-a', default='sum', help='聚合函数（默认: sum）')
    parser.add_argument('--type', '-t', choices=['bar', 'line', 'scatter', 'pie', 'hist'],
                       help='图表类型')
    parser.add_argument('--x', help='X轴列名')
    parser.add_argument('--y', help='Y轴列名')
    parser.add_argument('--date', help='日期列名')
    parser.add_argument('--value', help='数值列名')
    parser.add_argument('--freq', default='M', choices=['D', 'W', 'M', 'Q'],
                       help='时间频率（默认: M）')
    parser.add_argument('--fill', choices=['mean', 'median', 'mode', 'drop'],
                       help='缺失值填充方式')

    args = parser.parse_args()

    try:
        analyzer = ExcelAnalyzer(args.file)

        if args.command == 'info':
            analyzer.info()

        elif args.command == 'stats':
            analyzer.stats(args.columns)

        elif args.command == 'clean':
            if not args.output:
                print("错误: 清洗命令需要指定 --output 参数")
                sys.exit(1)
            analyzer.clean(args.output, fill_missing=args.fill)

        elif args.command == 'pivot':
            if not args.index or not args.values:
                print("错误: 透视表需要指定 --index 和 --values 参数")
                sys.exit(1)
            analyzer.pivot(args.index, args.values, args.aggfunc, output_path=args.output)

        elif args.command == 'chart':
            if not args.type or not args.x or not args.y:
                print("错误: 图表需要指定 --type, --x 和 --y 参数")
                sys.exit(1)
            analyzer.chart(args.type, args.x, args.y)

        elif args.command == 'correlation':
            analyzer.correlation(args.columns)

        elif args.command == 'trend':
            if not args.date or not args.value:
                print("错误: 趋势分析需要指定 --date 和 --value 参数")
                sys.exit(1)
            analyzer.trend(args.date, args.value, args.freq)

        elif args.command == 'full':
            if not args.output:
                print("错误: 完整报告需要指定 --output 参数")
                sys.exit(1)
            analyzer.full_report(args.output)

    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
