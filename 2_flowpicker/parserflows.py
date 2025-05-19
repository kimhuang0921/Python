import os
import re
import csv

def extract_flow_and_patterns_from_text(flow_text):
    results = []

    # 抓出 flow 名稱與其完整區塊
    flow_blocks = re.findall(r'flow\s+(\S+)\s*\{(.*?)\n\}', flow_text, re.DOTALL)

    for flow_name, content in flow_blocks:
        # 每個 suite 區塊
        suite_blocks = re.findall(
            r'suite\s+(\S+)\s+calls\s+digital\.FunctionalTest_wo_profiling\s*\{(.*?)\}',
            content,
            re.DOTALL
        )

        for suite_name, suite_content in suite_blocks:
            # 抓 operatingSequence
            opseq_match = re.search(r'operatingSequence\s*=\s*setupRef\((.*?)\)', suite_content)
            if opseq_match:
                opseq = opseq_match.group(1).strip()
                parts = opseq.split('.')
                if len(parts) >= 3:
                    flow_location = parts[1]       # 第二段，例如 DEBUG_0424_DMS
                    pattern_name = parts[-2]       # 倒數第二段為 pattern name
                    results.append((flow_name, suite_name, flow_location, pattern_name))
    return results

def process_all_flows(root_dir, output_csv="all_patterns.csv"):
    all_results = []

    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".flow"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        entries = extract_flow_and_patterns_from_text(text)
                        all_results.extend(entries)
                except Exception as e:
                    print(f"[WARN] 無法讀取 {full_path}：{e}")

    # 寫入 CSV
    with open(output_csv, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Flow Name", "Suite Name", "Flow Location", "Pattern Name"])
        writer.writerows(all_results)

    print(f"[INFO] 完成，結果輸出至 {output_csv}，共 {len(all_results)} 筆資料")

# === ✏️ 你可以修改這裡設定資料夾路徑 ===
if __name__ == "__main__":
    input_folder = "/Users/kimhuang/Downloads/Flows"  # ← 改成你的 flow 資料夾路徑
    process_all_flows(input_folder)
