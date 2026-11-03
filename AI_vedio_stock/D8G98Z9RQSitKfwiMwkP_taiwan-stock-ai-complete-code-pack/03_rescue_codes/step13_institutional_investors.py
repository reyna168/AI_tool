這是我準備好的 STEP 13 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 13: 落後指標綜合熱力圖 - 備用救援程式碼
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

corr_data = pd.DataFrame(index=df.index)
corr_data['Close_Price'] = df['close']
corr_data['Volume'] = df['volume']
corr_data['Margin_Balance'] = df['margin_balance'] if 'margin_balance' in df.columns else np.random.randint(1000, 5000, len(df))
corr_data['Short_Balance'] = df['short_balance'] if 'short_balance' in df.columns else np.random.randint(100, 500, len(df))

if 'foreign_cum' in df.columns:
    corr_data['Foreign_Cum'] = df['foreign_cum']
else:
    corr_data['Foreign_Cum'] = np.random.randn(len(df)).cumsum() * 1000

corr_matrix = corr_data.corr()

plt.figure(figsize=(8, 6), dpi=120)
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=1, vmin=-1, vmax=1)
plt.title('2330 Indicators Correlation Matrix (Lagging & Fundamentals)')
plt.tight_layout()
plt.show()

top_corr = corr_matrix['Close_Price'].drop('Close_Price').abs().idxmax()
top_corr_val = corr_matrix['Close_Price'][top_corr]
print(f"📊 與台積電收盤價相關性最高之落後指標為: {top_corr} (相關係數: {top_corr_val:.2f})")
```
