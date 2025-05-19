import csv
import re
import os

# 讀取 0519_final_scan.csv，提取 Flow Name 和 Flow Location
flow_names = set()
flow_locations = set()
csv_rows = []
try:
    with open('0519_final_scan.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if 'Flow Name' in row and 'Flow Location' in row:
                flow_names.add(row['Flow Name'].strip())
                flow_locations.add(row['Flow Location'].strip())
                csv_rows.append({
                    'update name': row.get('update name', '').strip(),
                    'Flow Name': row['Flow Name'].strip(),
                    'Flow Location': row['Flow Location'].strip(),
                    'Mask_Status': 'Not found',
                    'Problem_Reason': 'Flow not in file'  # 初始假設
                })
except FileNotFoundError:
    print("錯誤：未找到 0519_final_scan.csv，請確認文件路徑")
    exit(1)
except Exception as e:
    print(f"讀取 CSV 文件時發生錯誤：{e}")
    exit(1)

# 指定主資料夾路徑（請替換為實際路徑）
main_folder = '/Users/kimhuang/1_Pythons/2_flowpicker/Flows'  # 例如：/home/user/project/mainflow/
output_folder = os.path.join(os.path.dirname(main_folder), 'update')

# 創建輸出資料夾
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 處理單個 flow 文件（MainFlow.flow 或 DEBUG_xxx.flow）
def process_main_flow(input_path, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        with open(input_path, 'r', encoding='utf-8') as flowfile:
            main_flow_content = flowfile.readlines()
    except Exception as e:
        print(f"無法讀取 {input_path}：{e}")
        return {}

    # 第一遍：Unmask 所有 flow 相關行（移除 //）
    temp_content = []
    in_setup = False
    in_execute = False
    flow_lines = []
    flow_name = None
    for line in main_flow_content:
        stripped_line = line.strip()

        if re.match(r'\s*setup\s*{', stripped_line, re.IGNORECASE):
            in_setup = True
            temp_content.append(line)
            continue
        if re.match(r'\s*execute\s*{', stripped_line, re.IGNORECASE):
            in_execute = True
            temp_content.append(line)
            continue
        if (in_setup or in_execute) and re.match(r'\s*}', stripped_line):
            in_setup = False
            in_execute = False
            temp_content.append(line)
            continue

        if in_setup:
            match = re.match(r'\s*flow\s+(\S+)\s+calls\s+Flows\.[\w.]+\s*{', stripped_line)
            if match:
                flow_name = match.group(1)
                flow_lines = [line.lstrip('/') if line.strip().startswith('//') else line]
                if stripped_line.endswith('}'):
                    temp_content.extend(flow_lines)
                    flow_lines = []
                    flow_name = None
                continue
            if flow_lines and re.match(r'\s*}', stripped_line):
                flow_lines.append(line.lstrip('/') if line.strip().startswith('//') else line)
                temp_content.extend(flow_lines)
                flow_lines = []
                flow_name = None
                continue
            if flow_lines:
                flow_lines.append(line.lstrip('/') if line.strip().startswith('//') else line)
                continue
            temp_content.append(line)
        elif in_execute:
            match = re.match(r'\s*(?:flow\s+)?(\S+)\.execute\s*\(\);', stripped_line)
            if match:
                temp_content.append(line.lstrip('/') if line.strip().startswith('//') else line)
            else:
                temp_content.append(line)
        else:
            temp_content.append(line)

    # 第二遍：根據 flow_names 重新 mask
    new_flow_content = []
    in_setup = False
    in_execute = False
    flow_lines = []
    flow_name = None
    mask_status = {}

    i = 0
    while i < len(temp_content):
        line = temp_content[i]
        stripped_line = line.strip()

        if re.match(r'\s*setup\s*{', stripped_line, re.IGNORECASE):
            in_setup = True
            print(f"進入 setup 區塊：{input_path}, 行 {i+1}")
            new_flow_content.append(line)
            i += 1
            continue
        if re.match(r'\s*execute\s*{', stripped_line, re.IGNORECASE):
            in_execute = True
            print(f"進入 execute 區塊：{input_path}, 行 {i+1}")
            new_flow_content.append(line)
            i += 1
            continue
        if (in_setup or in_execute) and re.match(r'\s*}', stripped_line):
            if in_setup:
                print(f"離開 setup 區塊：{input_path}, 行 {i+1}")
            elif in_execute:
                print(f"離開 execute 區塊：{input_path}, 行 {i+1}")
            in_setup = False
            in_execute = False
            new_flow_content.append(line)
            i += 1
            continue

        if in_setup:
            match = re.match(r'\s*flow\s+(\S+)\s+calls\s+Flows\.[\w.]+\s*{', stripped_line)
            if match:
                flow_name = match.group(1)
                flow_lines = [line]
                if stripped_line.endswith('}'):
                    if flow_name not in flow_names:
                        new_flow_content.extend([f'//{l}' for l in flow_lines])
                        mask_status[flow_name] = mask_status.get(flow_name, set()) | {'setup'}
                    else:
                        new_flow_content.extend(flow_lines)
                        mask_status[flow_name] = mask_status.get(flow_name, set()) | {'not_masked'}
                    flow_lines = []
                    flow_name = None
                i += 1
                continue
            if flow_lines and re.match(r'\s*}', stripped_line):
                flow_lines.append(line)
                if flow_name not in flow_names:
                    new_flow_content.extend([f'//{l}' for l in flow_lines])
                    mask_status[flow_name] = mask_status.get(flow_name, set()) | {'setup'}
                else:
                    new_flow_content.extend(flow_lines)
                    mask_status[flow_name] = mask_status.get(flow_name, set()) | {'not_masked'}
                flow_lines = []
                flow_name = None
                i += 1
                continue
            if flow_lines:
                flow_lines.append(line)
                i += 1
                continue
            new_flow_content.append(line)
            i += 1
        elif in_execute:
            match = re.match(r'\s*(?:flow\s+)?(\S+)\.execute\s*\(\);', stripped_line)
            if match:
                flow_name = match.group(1)
                print(f"處理 execute 行：{flow_name}, 行 {i+1}")
                if flow_name not in flow_names:
                    new_flow_content.append(f'//{line}')
                    mask_status[flow_name] = mask_status.get(flow_name, set()) | {'execute'}
                else:
                    new_flow_content.append(line)
                    mask_status[flow_name] = mask_status.get(flow_name, set()) | {'not_masked'}
            else:
                print(f"未匹配 execute 行：{stripped_line}, 行 {i+1}")
                new_flow_content.append(line)
            i += 1
        else:
            new_flow_content.append(line)
            i += 1

    try:
        with open(output_path, 'w', encoding='utf-8') as flowfile:
            flowfile.writelines(new_flow_content)
        print(f"已更新 {output_path}")
    except Exception as e:
        print(f"無法保存 {output_path}：{e}")

    return mask_status

# 處理 Flow Location 中指定的子資料夾
all_mask_status = {}
for location in flow_locations:
    cleaned_location = location.strip()
    input_subfolder = os.path.join(main_folder, cleaned_location)

    # 優先檢查 MainFlow.flow
    input_path_main = os.path.join(input_subfolder, 'MainFlow.flow')
    output_subfolder = os.path.join(output_folder, cleaned_location)
    output_path_main = os.path.join(output_subfolder, 'MainFlow.flow')

    # 如果沒有 MainFlow.flow，檢查 DEBUG_<location>.flow
    input_path_debug = os.path.join(input_subfolder, f'{cleaned_location}.flow')
    output_path_debug = os.path.join(output_subfolder, f'{cleaned_location}.flow')

    if not os.path.isdir(input_subfolder):
        print(f"子資料夾不存在：{input_subfolder}")
        for row in csv_rows:
            if row['Flow Location'] == location:
                row['Problem_Reason'] = f'Subfolder not found: {input_subfolder}'
        continue

    print(f"找到子資料夾：{input_subfolder}")
    if os.path.exists(input_path_main):
        print(f"處理文件：{input_path_main}")
        mask_status = process_main_flow(input_path_main, output_path_main)
    elif os.path.exists(input_path_debug):
        print(f"未找到 MainFlow.flow，處理文件：{input_path_debug}")
        mask_status = process_main_flow(input_path_debug, output_path_debug)
    else:
        print(f"未找到 MainFlow.flow 或 DEBUG_{cleaned_location}.flow 在 {input_subfolder}")
        for row in csv_rows:
            if row['Flow Location'] == location:
                row['Problem_Reason'] = f'Flow file not found in {input_subfolder}'
        continue

    # 更新 mask 狀態
    for row in csv_rows:
        if row['Flow Location'] == location:
            flow_name = row['Flow Name']
            if flow_name in mask_status:
                status = mask_status[flow_name]
                if 'not_masked' in status:
                    row['Mask_Status'] = 'Not masked'
                    row['Problem_Reason'] = 'Processed successfully'
                elif 'setup' in status and 'execute' in status:
                    row['Mask_Status'] = 'Masked in setup and execute'
                    row['Problem_Reason'] = 'Processed successfully'
                elif 'setup' in status:
                    row['Mask_Status'] = 'Masked in setup'
                    row['Problem_Reason'] = 'Processed successfully'
                elif 'execute' in status:
                    row['Mask_Status'] = 'Masked in execute'
                    row['Problem_Reason'] = 'Processed successfully'
                all_mask_status[flow_name] = all_mask_status.get(flow_name, set()) | status
            else:
                row['Problem_Reason'] = f'Flow not in file: {flow_name}'

# 保存總結 CSV
summary_csv_path = 'summary_0519_final_scan.csv'
try:
    with open(summary_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['update name', 'Flow Name', 'Flow Location', 'Mask_Status', 'Problem_Reason']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"總結 CSV 已保存到 {summary_csv_path}")
except Exception as e:
    print(f"無法保存總結 CSV：{e}")

print("所有指定的 flow 文件已處理並保存到 update 資料夾")