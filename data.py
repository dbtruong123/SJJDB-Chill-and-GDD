import pandas as pd

def load_input():
    df = pd.read_json("data.json")
    df.head()

    df1 = pd.DataFrame(df["Data"].iloc[0][0])
    df1.head()

    return df1