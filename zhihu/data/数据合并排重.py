import os
import pandas as pd

# 处理并合并CSV文件的操作
def merge_csv_files(folder_path, output_file):
    # 获取所有CSV文件（按文件名前的数字顺序排序）
    csv_files = sorted(
        [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.csv')],
        key=lambda x: int(os.path.basename(x).split('_')[0])  # 按编号排序
    )

    # 读取并合并所有CSV文件
    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, encoding='utf-8', low_memory=False, dtype=str)  # 读取为字符串，防止数据类型错误
            df_list.append(df)
        except Exception as e:
            print(f"⚠️ 读取文件 {file} 失败，错误: {e}")

    # 合并所有数据
    if df_list:
        merged_df = pd.concat(df_list, ignore_index=True, sort=False)  # sort=False 避免列顺序打乱

        # 去重操作，根据 'content_url' 列去重
        merged_df = merged_df.drop_duplicates(subset='content_url', keep='first')

        # 保存合并后的CSV文件
        merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 输出基础信息
        print("\n📊 合并后的数据基础信息：")
        print(f"✅ 合并完成，结果保存为 `{output_file}`")
        print(f"📌 总行数（数据条数）: {merged_df.shape[0]}")
        print(f"📌 总列数（字段个数）: {merged_df.shape[1]}")
        print(f"📌 列名列表: {list(merged_df.columns)}")

        print("\n📌 数据预览（前 5 行）：")
        print(merged_df.head())

        print("\n📌 数据类型统计：")
        print(merged_df.dtypes)

    else:
        print("❌ 没有成功读取任何 CSV 文件，请检查文件格式！")

# 主函数，进行数据处理
def main():
    folder_path = "zhihu"  # CSV 文件存储的文件夹
    output_file = "merged_zhihu.csv"  # 合并后的文件名
    merge_csv_files(folder_path, output_file)  # 执行合并操作

if __name__ == "__main__":
    main()
