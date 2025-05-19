import pandas as pd
import re
from pathlib import Path
import datetime

def load_csv_files(target_file, patterns_file):
    """載入 CSV 文件並返回 DataFrame"""
    try:
        target_df = pd.read_csv(target_file)
        patterns_df = pd.read_csv(patterns_file)
        return target_df, patterns_df
    except Exception as e:
        print(f"載入 CSV 文件時發生錯誤: {e}")
        return None, None

def extract_timestamp(pattern_name):
    """從 Pattern Name 中提取時間戳，格式為 _MMDDYY_X"""
    match = re.search(r'_(\d{6})_(\d)$', pattern_name)
    if match:
        timestamp = match.group(1)  # MMDDYY
        version = match.group(2)    # X
        try:
            # 將 MMDDYY 轉為 datetime 對象，假設年份為 20YY
            dt = datetime.datetime.strptime(f"20{timestamp[4:6]}-{timestamp[0:2]}-{timestamp[2:4]}", "%Y-%m-%d")
            # 使用 version 作為次序（次要排序）
            return dt, int(version)
        except ValueError:
            return None, None
    return None, None

def find_pattern_matches(target_suite, patterns_df):
    """為給定的 suite 查找所有匹配的模式，檢查 target_suite 是否包含在 Pattern Name 中"""
    # 使用 str.contains 檢查 Pattern Name 是否包含 target_suite，忽略大小寫
    matches = patterns_df[patterns_df['Pattern Name'].str.contains(re.escape(target_suite), case=False, na=False)]
    return matches

def generate_report(target_df, patterns_df, output_file):
    """生成報告並保存到 CSV，標記最新版本"""
    results = []
    
    for _, row in target_df.iterrows():
        suite = row['input suite']
        matches = find_pattern_matches(suite, patterns_df)
        
        if not matches.empty:
            # 為每個匹配提取時間戳
            matches = matches.copy()  # 避免修改原始 DataFrame
            matches['Timestamp'] = matches['Pattern Name'].apply(lambda x: extract_timestamp(x)[0])
            matches['Version'] = matches['Pattern Name'].apply(lambda x: extract_timestamp(x)[1])
            
            # 找出最新版本（按 Timestamp 和 Version 排序）
            if matches['Timestamp'].notna().any():
                latest_match = matches.dropna(subset=['Timestamp']).sort_values(
                    by=['Timestamp', 'Version'], ascending=[False, False]
                ).head(1)
                latest_pattern = latest_match['Pattern Name'].iloc[0] if not latest_match.empty else None
            else:
                latest_pattern = None
            
            # 為每個匹配生成結果
            for _, match in matches.iterrows():
                results.append({
                    'Target Suite': suite,
                    'Flow Name': match['Flow Name'],
                    'Suite Name': match['Suite Name'],
                    'Flow Location': match['Flow Location'],
                    'Pattern Name': match['Pattern Name'],
                    'Is Latest': 'Yes' if match['Pattern Name'] == latest_pattern else 'No'
                })
        else:
            results.append({
                'Target Suite': suite,
                'Flow Name': '無匹配',
                'Suite Name': '無匹配',
                'Flow Location': '無匹配',
                'Pattern Name': '無匹配',
                'Is Latest': 'N/A'
            })
    
    # 轉換為 DataFrame
    result_df = pd.DataFrame(results)
    
    # 保存到 CSV
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"報告已保存到 {output_file}")

def main():
    # 文件路徑
    target_file = 'TargetScanPatternsV2.csv'
    patterns_file = 'all_patterns.csv'
    output_file = f'pattern_matches_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    # 載入 CSV 文件
    target_df, patterns_df = load_csv_files(target_file, patterns_file)
    
    if target_df is None or patterns_df is None:
        print("無法繼續處理，因為 CSV 文件載入失敗。")
        return
    
    # 生成報告
    generate_report(target_df, patterns_df, output_file)

if __name__ == '__main__':
    main()