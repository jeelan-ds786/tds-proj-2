import os
import sys
import argparse 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import openai
import numpy as np

#Function to get API token from (.env file  or from setting in Environment variable)
def get_api_token():
    """Get API token from either an environment variable or command-line argument."""
    token = os.getenv("AIPROXY_TOKEN")
    if token:
        print("AIPROXY_TOKEN found in environment variables.")
    return token

#Function to create folder with name of dataset and save AI generated README.md and *.png files 
def create_output_directory(file_path):
    """Create a directory based on the input file name."""
    base_name = os.path.splitext(os.path.basename(file_path))[0]  
    output_dir = os.path.join(os.getcwd(), base_name)
    os.makedirs(output_dir, exist_ok=True)  
    return output_dir

# Function to setting up API key and start data analysis (Data loading --> AI-gen narrative story)
def analyze_file(file_path, token):
    # Set up OpenAI API
    openai.api_base = "https://aiproxy.sanand.workers.dev/openai/v1"
    openai.api_key = token
    # Create an output directory for the current file
    output_dir = create_output_directory(file_path)
    print(f"Output directory created: {output_dir}")
    
    # Determine the file type based on its extension
    file_extension = os.path.splitext(file_path)[1].lower()
    print(f"Detected file extension: {file_extension}")

    # Loading the dataset (all formats like .csv , .xls , .xlsx)
    try:
        if file_extension == ".csv":
            print("Loading CSV file with fallback encodings...")
            try:
                data = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                print("Failed to load with utf-8, trying ISO-8859-1...")
                data = pd.read_csv(file_path, encoding='ISO-8859-1')
        elif file_extension in [".xls", ".xlsx"]:
            print("Loading Excel file...")
            data = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")
        print("File loaded successfully.")
    except Exception as e:
        print(f"Error loading file: {e}")
        raise ValueError(f"Error loading file: {e}")
    
    #  Data Cleaning Section
    try:
        print("Cleaning and converting data types...")

        # Replace blank/empty strings with NaN
        data.replace(r'^\s*$', np.nan, regex=True, inplace=True)


    except Exception as e:
        print(f"Error during data cleaning: {e}")
        raise ValueError(f"Error during data cleaning: {e}")
    

    # Basic data exploration
    try:
        print("Generating summary statistics...")
        summary_stats = data.describe(include="all").to_string()
        data_types = data.dtypes.to_string()
        missing_values = data.isnull().sum()
        missing_percentage = (missing_values / len(data)) * 100
        missing_report = pd.DataFrame({
            "Missing Values": missing_values,
            "Percentage": missing_percentage
        })

        # Outlier detection using IQR
        print("Detecting outliers...")
        numeric_data = data.select_dtypes(include=[np.number])
        Q1 = numeric_data.quantile(0.25)
        Q3 = numeric_data.quantile(0.75)
        IQR = Q3 - Q1
        outliers = ((numeric_data < (Q1 - 1.5 * IQR)) | (numeric_data > (Q3 + 1.5 * IQR))).sum()

        # Plot 1 : ( correlation Matrix plot)
        print("Creating correlation matrix plot...")
        plt.figure(figsize=(10, 8))
        sns.heatmap(numeric_data.corr(), annot=True, cmap="coolwarm", fmt=".2f", square=True)
        plt.title("Correlation Matrix")
        path = os.path.join(output_dir, "correlation_matrix.png")
        plt.savefig(path)
        plt.close()
        print("Correlation matrix plot saved as 'correlation_matrix.png'.")
        
        # Plot 2 : ( Missing value heatmap)
        print("Creating missing values heatmap...")
        plt.figure(figsize=(10, 6))
        sns.heatmap(data.isnull(), cbar=False, cmap='viridis')
        plt.title("Missing Values Heatmap")
        path = os.path.join(output_dir, "missing_values_heatmap.png")
        plt.savefig(path)
        plt.close()
        print("Missing values heatmap saved as 'missing_values_heatmap.png'.")

        # Plot 3 : (boxplot for outliers)
        print("Creating boxplot for outliers...")
        plt.figure(figsize=(12, 8))
        sns.boxplot(data=numeric_data)
        plt.xticks(rotation=45)
        plt.title("Outlier Detection (Boxplot)")
        path = os.path.join(output_dir, "outlier_boxplot.png")
        plt.savefig(path)
        plt.close()
        print("Boxplot saved as 'outlier_boxplot.png'.")

        # Plot 4 : (histogram plot)
        print("Creating histograms...")
        numeric_data.hist(figsize=(12, 10), bins=30)
        plt.suptitle("Histograms of Numerical Features")
        path = os.path.join(output_dir, "numerical_histograms.png")
        plt.savefig(path)
        plt.close()
        print("Histograms saved as 'numerical_histograms.png'.")
        
        # Plot 5 : (Bar Plot)
        print("Creating bar plots for categorical data...")
        categorical_data = data.select_dtypes(include=['object'])
        for col in categorical_data.columns:
            top_categories = data[col].value_counts().nlargest(10)  # Get the top 10 categories
            plt.figure(figsize=(10, 6))
            sns.barplot(x=top_categories.values, y=top_categories.index, palette="viridis")
            plt.title(f"Top 10 Distribution of {col}")
            plt.xlabel("Count")
            plt.ylabel(col)
            plt.tight_layout()
            path = os.path.join(output_dir, f"{col}_top10_distribution.png")
            plt.savefig(path)
            plt.close()
            print(f"Bar plot for top 10 categories saved as '{col}_top10_distribution.png'.")
            print("Creating bar plots for the least frequent categories in categorical data...")
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise

    # prompt to execute by the gpt-4o-mini 
    narrative_prompt = f"""
You are a data analyst tasked with creating a comprehensive, human-readable analysis story for a dataset loaded from the file `{os.path.basename(file_path)}`. This dataset contains a mix of numerical and categorical features. Your objective is to provide a compelling narrative that includes detailed analysis and a visually appealing README file with the following sections:

---

## **1. Project Overview**
- **Dataset Name**: `{os.path.basename(file_path)}`
- **Dataset Description**: Briefly describe the purpose or origin of the dataset (e.g., "This dataset provides information about XYZ.").
- **Summary Statistics**: Provide an overview of key metrics like:
  - Total Features: {len(data.columns)}
  - Total Records: {len(data)}
  - Data Types: Numerical ({len(data.select_dtypes(include='number').columns)}), Categorical ({len(data.select_dtypes(include='object').columns)})

---

## **2. Data Cleaning Process**
- **Missing Data**: Describe how missing values were handled (e.g., dropped, imputed) for columns where missing values exceeded 10% ({', '.join(missing_report[missing_report > 10].index.tolist())}).
- **Outliers**: Highlight the columns with detected outliers ({', '.join(outliers[outliers > 0].index.tolist())}) and explain their potential causes and impact.
- **Formatting Changes**: Mention any transformations applied (e.g., date formatting, standardizing units).

---

## **3. Exploratory Data Analysis (EDA)**

- **Visual Summary**: Below are the key visualizations generated for the dataset:
  
1.- [Correlation Heatmap](./correlation_matrix.png)
 ***Correlation Heatmap***: What are the significant correlations in the dataset (above 0.7 or below -0.7)?
  - [Box Plot for Outliers](./outlier_boxplot.png)
2. **Box Plot for Outliers**: Are there any columns with outliers? How might they affect data analysis or modeling?
  - [Missing Values Heatmap](./missing_values_heatmap.png)
3. **Missing Values Heatmap**: Which columns have missing values, and what percentage of data is missing?
  - [Histograms of Numerical Features](./numerical_histograms.png)
4. **Histograms of Numerical Features**: Which features are skewed or have unusual distributions?


## **4. Key Insights**
- **Feature Importance**: Highlight standout features with potential predictive power.
- **Data Quality**: Summarize issues such as missing data or inconsistent entries.
- **Patterns & Trends**: Provide actionable insights (e.g., "Feature X is a strong predictor of Y.").

---

## **5. Recommendations**
- **Data Preparation**: Suggest further steps for improving data quality (e.g., advanced imputation methods, removing anomalies).
- **Modeling Tips**:
  - Address multicollinearity in highly correlated features.
  - Recommend feature scaling or normalization techniques.
- **Feature Engineering**: Propose creating new features (e.g., ratios, log transformations) to improve predictive power.

---

## **6. Appendix**
- **File Details**:
  - Dataset Path: `{file_path}`
- **Additional Visualizations**: Attach links to saved plots and images.
- **Images Analysis**: Summarize key insights from accompanying images if any.

---

## **7. References**
Provide links to:
- Documentation
- Related articles or papers about the dataset's domain.
- External sources of analysis inspiration.

"""
    
    # generating Response from LLM model
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst."}, 
                {"role": "user", "content": narrative_prompt}
            ],
            max_tokens=150,
            temperature=0.3,
            
        )
        narrative = response['choices'][0]['message']['content']
        readme_path = os.path.join(output_dir, "README.md")
        
        with open(readme_path, "w") as f:
            f.write(narrative)
            print(f"Narrative report saved as '{readme_path}'.")
    #handling mutliple exceptions
    except openai.error.AuthenticationError as e:
        print(f"Authentication Error: {e}. Please check your API token.")
    except openai.error.OpenAIError as e:
        print(f"OpenAI API Error: {e}. Path: {openai.api_base}/chat/completions")
    except Exception as e:
        print(f"Unexpected error occurred while generating narrative: {e}")


# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a CSV or Excel file and generate an analysis report.")
    parser.add_argument('file_path', type=str, help="Path to the file (CSV or Excel) to be analyzed.")
    parser.add_argument('--token', type=str, help="AI Proxy token (optional, can also be set via AIPROXY_TOKEN env variable).")
    args = parser.parse_args()

    # Get the token from arguments or environment variable (another method to fetch API token)
    token = args.token if args.token else get_api_token()
    if not token:
        raise ValueError("AIPROXY_TOKEN is not set! Please provide it as an environment variable or via --token argument.")
    
    file_path = args.file_path  # Get the file path from the command-line arguments
    print(f"Starting analysis for file: {file_path}")
    
    try:
        analyze_file(file_path, token)
        print("Analysis complete!")
    except Exception as e:
        print(f"An error occurred during analysis: {e}")


