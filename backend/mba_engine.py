import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from mlxtend.frequent_patterns import apriori, association_rules
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class MBAEngine:
    def __init__(self, filepath, output_dir='./outputs'):
        self.filepath = filepath
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.df = None
        self.basket = None
        self.frequent_itemsets = None
        self.rules = None
        self.strong_rules = None

    def _load_and_clean(self):
        """Load CSV, auto-detect separator, handle missing columns, and clean."""
        # Detect separator automatically
        with open(self.filepath, 'r', encoding='latin-1') as f:
            first_line = f.readline()
            sep = ';' if ';' in first_line else ','

        df = pd.read_csv(self.filepath, sep=sep, encoding='latin-1', low_memory=False)

        # Print column names for debugging
        print("Columns in CSV:", df.columns.tolist())

        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()

        # If 'BillNo' is missing, try to find a matching column
        if 'BillNo' not in df.columns:
            for col in df.columns:
                if 'bill' in col.lower() or 'invoice' in col.lower():
                    df.rename(columns={col: 'BillNo'}, inplace=True)
                    break
            else:
                raise KeyError(f"Column 'BillNo' not found. Available columns: {df.columns.tolist()}")

        # Keep only required columns
        required = ['BillNo', 'Itemname', 'Quantity']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns: {missing}. Found: {df.columns.tolist()}")

        df = df[required].copy()

        # Drop rows with missing values in these columns
        df.dropna(subset=['BillNo', 'Itemname', 'Quantity'], inplace=True)

        # Ensure Quantity is numeric and positive
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        df.dropna(subset=['Quantity'], inplace=True)
        df = df[df['Quantity'] > 0]

        # Clean BillNo and Itemname (strip spaces, uppercase)
        df['BillNo'] = df['BillNo'].astype(str).str.strip()
        df['Itemname'] = df['Itemname'].astype(str).str.strip().str.upper()

        # Remove cancelled transactions (BillNo starting with 'C')
        df = df[~df['BillNo'].str.startswith('C')]
        df = df[df['Itemname'] != '']

        self.df = df
        print(f"Cleaned data: {len(df)} rows, {df['BillNo'].nunique()} transactions, {df['Itemname'].nunique()} products")
        return df

    def _create_basket(self, min_freq=20):
        """Create binary basket and filter products with support >= min_freq."""
        # If BillNo is the index, reset it
        if self.df.index.name == 'BillNo':
            self.df = self.df.reset_index()

        # Group and unstack
        grouped = self.df.groupby(['BillNo', 'Itemname'])['Quantity'].sum()
        if grouped.empty:
            raise ValueError("No transactions found after cleaning. Check your data.")

        basket = grouped.unstack(fill_value=0)
        basket = (basket > 0).astype('int8')

        # Filter products
        freq = basket.sum(axis=0)
        basket_filtered = basket.loc[:, freq >= min_freq]

        self.basket = basket_filtered
        print(f"Basket shape: {self.basket.shape} (transactions: {self.basket.shape[0]}, products: {self.basket.shape[1]})")
        return basket_filtered

    def _plot_top_items(self, top_n=20):
        items = self.frequent_itemsets.head(top_n).copy()
        items['item'] = items['itemsets'].apply(lambda x: ', '.join(sorted(list(x))))
        plt.figure(figsize=(12, 6))
        sns.barplot(data=items, x='support', y='item', palette='viridis')
        plt.title(f'Top {top_n} Most Frequent Items')
        plt.xlabel('Support')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'top_items.png'), dpi=150)
        plt.close()

    def _plot_support_distribution(self):
        plt.figure(figsize=(10, 5))
        sns.histplot(self.frequent_itemsets['support'], bins=30, kde=True, color='skyblue')
        plt.title('Support Distribution')
        plt.xlabel('Support')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'support_dist.png'), dpi=150)
        plt.close()

    def _plot_top_rules_lift(self, top_n=10):
        top = self.rules.nlargest(top_n, 'lift').copy()
        top['rule'] = top.apply(
            lambda r: f"{', '.join(sorted(list(r['antecedents'])))} → {', '.join(sorted(list(r['consequents'])))}",
            axis=1
        )
        plt.figure(figsize=(12, 6))
        sns.barplot(data=top, x='lift', y='rule', palette='coolwarm')
        plt.title(f'Top {top_n} Rules by Lift')
        plt.xlabel('Lift')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'top_rules_lift.png'), dpi=150)
        plt.close()

    def _plot_support_vs_confidence(self):
        plt.figure(figsize=(10, 6))
        sc = plt.scatter(self.rules['support'], self.rules['confidence'],
                         c=self.rules['lift'], cmap='viridis', alpha=0.6, edgecolors='w')
        plt.colorbar(sc, label='Lift')
        plt.xlabel('Support')
        plt.ylabel('Confidence')
        plt.title('Support vs Confidence (colored by Lift)')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'support_vs_confidence.png'), dpi=150)
        plt.close()

    def _plot_confidence_vs_lift(self):
        plt.figure(figsize=(10, 6))
        plt.scatter(self.rules['confidence'], self.rules['lift'], alpha=0.6, color='teal')
        plt.xlabel('Confidence')
        plt.ylabel('Lift')
        plt.title('Confidence vs Lift')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'confidence_vs_lift.png'), dpi=150)
        plt.close()

    def run(self, min_support=0.02, min_confidence=0.1, min_freq=20):
        """Execute the full MBA pipeline."""
        self._load_and_clean()
        self._create_basket(min_freq)

        # Apriori
        self.frequent_itemsets = apriori(self.basket, min_support=min_support,
                                         use_colnames=True, max_len=2, low_memory=True)
        self.frequent_itemsets = self.frequent_itemsets.sort_values('support', ascending=False).reset_index(drop=True)

        # Rules
        self.rules = association_rules(self.frequent_itemsets, metric='confidence', min_threshold=min_confidence)

        # Strong rules
        self.strong_rules = self.rules[(self.rules['confidence'] >= 0.5) & (self.rules['lift'] > 1)].copy()
        self.strong_rules = self.strong_rules.sort_values('lift', ascending=False).reset_index(drop=True)

        # Save strong rules as CSV
        if not self.strong_rules.empty:
            recs = self.strong_rules[['antecedents', 'consequents', 'confidence', 'lift']].copy()
            recs['antecedents'] = recs['antecedents'].apply(lambda x: ', '.join(sorted(list(x))))
            recs['consequents'] = recs['consequents'].apply(lambda x: ', '.join(sorted(list(x))))
            recs['confidence'] = (recs['confidence'] * 100).round(2)
            recs.columns = ['If Customer Buys', 'Recommend', 'Confidence (%)', 'Lift']
            recs.to_csv(os.path.join(self.output_dir, 'product_recommendations.csv'), index=False)

        # Generate plots
        self._plot_top_items()
        self._plot_support_distribution()
        self._plot_top_rules_lift()
        self._plot_support_vs_confidence()
        self._plot_confidence_vs_lift()

        print("MBA analysis complete.")
        return self

    def recommend(self, product_name, top_n=5):
        """Return top N recommendations for a product."""
        product_name = product_name.strip().upper()
        matches = self.rules[self.rules['antecedents'].apply(lambda x: product_name in x)].copy()
        matches = matches[matches['lift'] > 1].sort_values('lift', ascending=False).head(top_n)
        if matches.empty:
            return pd.DataFrame(columns=['antecedents', 'consequents', 'confidence', 'lift'])
        result = matches[['antecedents', 'consequents', 'confidence', 'lift']].copy()
        result['antecedents'] = result['antecedents'].apply(lambda x: ', '.join(sorted(list(x))))
        result['consequents'] = result['consequents'].apply(lambda x: ', '.join(sorted(list(x))))
        result['confidence'] = (result['confidence'] * 100).round(2)
        result['lift'] = result['lift'].round(2)
        return result