input_str = input('请输入要去重的字符串：')

# 分割 + 去重 + 保留顺序
unique_names = list(dict.fromkeys(input_str.split("\\")))

# 再合并为字符串
result = "\\\\".join(unique_names)

print(result)
