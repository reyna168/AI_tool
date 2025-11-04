

https://hackmd.io/YfjLt5TjRKaBfpAWrXolDw#Streambench-Final-Project

我們在 Prompt 中引入了 Chain-of-Thought 的方法，指導模型按照指定的步驟生成 SQL 查詢。以下是我們設計的 Prompt 問題分析步驟：

## 階段 1：搜尋相關的 Table 和 Column

要求模型首先分析輸入的使用者問題 (User Query)。
從提供的 Table Schema 和 Schema Information 中，找出與該問題相關的資料表和欄位，並提取其資訊。
結果須以以下格式輸出將使用的資料表和欄位：
OUTPUT FORMAT:  
Table1: Column1, Column2  
Table2: Column3, Column4  
Table3: Column5, etc.  

## 階段 2：生成 SQL 查詢

確定 User Query 所屬的問題類型，例如篩選條件 (Filters)、條件式 (Conditions)、聚合 (Aggregations)、關聯 (Relationships) 等。
根據上述分析結果，生成能夠回答 User Query 的 SQL 程式碼。
