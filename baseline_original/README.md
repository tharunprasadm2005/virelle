# Recipe Recommendation System

A comprehensive machine learning-based recipe recommendation system that provides personalized recipe suggestions using collaborative filtering, content-based filtering, and hybrid approaches.

## Dataset

This project uses the **Food.com Recipe and Interaction Dataset**, which contains:
- **180,000+ recipes** with ingredients, nutritional information, and user ratings
- **700,000+ user interactions** and reviews

### Dataset Attribution
- **Source**: Food.com (originally Recipe1M dataset)
- **Kaggle Dataset**: [Food.com Recipes and Interactions](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions)
- **Original Paper**: "Recipe1M+: A Dataset for Learning Cross-Modal Embeddings for Cooking Recipes and Food Images"
- **Citation**: If you use this dataset, please cite the original work

### Dataset Files Required
- `RAW_recipes.csv`: Recipe information including ingredients, tags, nutrition facts, and cooking time
- `RAW_interactions.csv`: User-recipe interactions with ratings and reviews

**Note**: Due to size constraints, the actual dataset files are not included in this repository. Please download them from the Kaggle link above and place them in the `data/code/datasets/` directory.

## Features

- **Hybrid Recommendation Engine**: Combines collaborative filtering (SVD) and content-based filtering (TF-IDF)
- **User Profile Management**: Supports dietary preferences, cuisine choices, and cooking time constraints
- **Interactive CLI Interface**: Easy-to-use command-line interface for new and existing users
- **Smart Categorization**: Automatic recipe categorization with clustering for uncategorized recipes
- **Rating System**: Users can rate recipes to improve future recommendations
- **Data Pipeline**: Complete preprocessing and model training pipeline

## Project Structure

```
recipe-recommendation-system/
├── data/
│   ├── Scripts/
│   │   ├── recommender_app.py              # Main recommendation application
│   │   ├── preprocess_recipes_and_build_initial_models.py  # Data preprocessing & model training
│   │   ├── preprocess_interactions.py      # Interaction data preprocessing
│   │   └── retrain_models.py              # Model retraining utilities
│   ├── code/
│   │   ├── datasets/                      # Raw data files (user must download)
│   │   │   ├── RAW_recipes.csv           # [DOWNLOAD REQUIRED]
│   │   │   ├── RAW_interactions.csv      # [DOWNLOAD REQUIRED]
│   │   │   └── README.md
│   │   └── *.ipynb                        # Jupyter notebooks for analysis
│   └── processed/                         # Generated processed data files
│       └── README.md
├── models/                                # Generated trained ML models
│   └── README.md
├── reports/                               # Generated visualization outputs
├── requirements.txt                       # Python dependencies
├── setup.py                             # Project setup script
├── QUICKSTART.md                         # Quick start guide
├── test_recommendations.py              # Test suite
├── project_health_check.py              # System validation
├── LICENSE                               # MIT License
└── README.md                            # This file
```

### Key Files Description
- **recommender_app.py**: Main CLI application for getting recommendations
- **preprocess_recipes_and_build_initial_models.py**: Complete data pipeline from raw data to trained models
- **setup.py**: Automated setup script for dependencies and NLTK data
- **QUICKSTART.md**: Step-by-step getting started guide

## Getting Started (Quick Setup)

### Prerequisites
- Python 3.8 or higher
- At least 4GB RAM (8GB recommended for preprocessing)
- 2GB free disk space
- Internet connection for downloading dependencies and dataset

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/recipe-recommendation-system.git
   cd recipe-recommendation-system
   ```

2. **Create and activate virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (macOS/Linux)
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Download NLTK data** (required for text processing):
   ```bash
   python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('punkt')"
   ```

### Data Setup

1. **Download the Food.com Dataset**:
   - Visit [Food.com Recipes and Interactions on Kaggle](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions)
   - Download the dataset (requires free Kaggle account)
   - Extract the files

2. **Place data files** in `data/code/datasets/`:
   ```
   data/code/datasets/
   ├── RAW_recipes.csv     (~500MB)
   └── RAW_interactions.csv (~300MB)
   ```

3. **Run preprocessing** to prepare the data and build initial models:
   ```bash
   python data/Scripts/preprocess_recipes_and_build_initial_models.py
   ```
   
   This step will:
   - Clean and process the recipe data
   - Extract features for content-based filtering
   - Filter and prepare interaction data for collaborative filtering
   - Train initial SVD and TF-IDF models
   - Create recipe clusters and categories
   - Generate processed files in `data/processed/` and `models/`

**⚠️ Important**: The preprocessing step may take 10-30 minutes depending on your system, as it processes 180K+ recipes and 700K+ interactions.

## Usage

### Running the Recommendation System

```bash
python data/Scripts/recommender_app.py
```

### Features Available:

1. **New User**: Create a profile with dietary preferences and get personalized recommendations
2. **Existing User**: Get recommendations based on past ratings and preferences
3. **Rating System**: Rate recommended recipes to improve future suggestions

### Sample Workflow:

1. **For New Users**:
   - Choose "New User" option
   - Create profile with dietary preferences (vegetarian, vegan, etc.)
   - Specify preferred cuisines and favorite ingredients
   - Set maximum cooking time
   - Receive personalized recommendations
   - Rate recipes to improve future suggestions

2. **For Existing Users**:
   - Choose "Existing User" option
   - Enter your User ID
   - Receive hybrid recommendations based on your history
   - Rate new recipes to update your profile

## Technical Details

### Machine Learning Models

1. **Collaborative Filtering**: 
   - **Algorithm**: SVD (Singular Value Decomposition) using scikit-surprise
   - **Purpose**: Predict user ratings based on similar users' preferences
   - **Features**: User-item interaction matrix with ratings 1-5

2. **Content-Based Filtering**: 
   - **Algorithm**: TF-IDF vectorization with cosine similarity
   - **Purpose**: Find recipes similar to those a user has liked
   - **Features**: Recipe text (name, description, ingredients, tags)

3. **Clustering**: 
   - **Algorithm**: K-Means clustering with optimal k selection
   - **Purpose**: Group similar recipes for better categorization
   - **Features**: Ingredient vectors, tag vectors, and nutritional data

4. **Hybrid Approach**: 
   - **Method**: Weighted combination of CF and content-based scores
   - **Weight**: 70% collaborative filtering + 30% content-based (configurable)
   - **Fallback**: Content-based and popularity-based for new users

### Key Technologies

- **Machine Learning**: scikit-learn, scikit-surprise
- **Data Processing**: pandas, numpy
- **Text Processing**: NLTK, TF-IDF vectorization
- **Similarity**: Cosine similarity, RapidFuzz for fuzzy matching
- **Database**: SQLite for user profiles and ratings
- **Visualization**: matplotlib, seaborn

## Data Processing Pipeline

1. **Recipe Preprocessing**:
   - Nutritional information extraction
   - Dietary restriction detection
   - Text feature preparation for content-based filtering
   - Recipe categorization and clustering

2. **Interaction Preprocessing**:
   - Data cleaning and deduplication
   - User/recipe activity filtering
   - Rating normalization

3. **Model Training**:
   - SVD model for collaborative filtering
   - TF-IDF vectorizer for content similarity
   - K-Means clustering for recipe grouping

## Testing and Validation

Run the test suite to verify everything is working:
```bash
python test_recommendations.py
python project_health_check.py
```

## Troubleshooting

### Common Issues

1. **"Dataset files not found"**
   - Ensure you've downloaded and placed `RAW_recipes.csv` and `RAW_interactions.csv` in `data/code/datasets/`
   - Check file names match exactly (case-sensitive)

2. **"scikit-surprise import error"**
   ```bash
   pip install scikit-surprise
   ```

3. **NLTK data missing**
   ```bash
   python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet')"
   ```

4. **Memory issues during preprocessing**
   - Close other applications
   - Use a machine with at least 8GB RAM
   - Consider processing a subset of data first

5. **Long preprocessing time**
   - This is normal - the full dataset preprocessing takes 15-30 minutes
   - You can monitor progress through the console output

### Performance Tips
- Use SSD storage for faster data loading
- Ensure sufficient RAM (8GB recommended)
- Close unnecessary applications during preprocessing

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## Future Improvements

- [ ] Web-based user interface
- [ ] Deep learning models for better recommendations
- [ ] Real-time recommendation updates
- [ ] Advanced user preference learning
- [ ] Recipe image analysis
- [ ] Social features (sharing, reviews)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Food.com** and **Kaggle** for providing the comprehensive recipe and interaction dataset
- **scikit-surprise** library developers for excellent collaborative filtering tools
- **scikit-learn** community for robust machine learning algorithms
- **NLTK** team for natural language processing capabilities
- Original researchers of the Recipe1M+ dataset for inspiring this work

## Dataset License

Please ensure compliance with the Food.com dataset license terms available on Kaggle. This project is for educational and research purposes.

## Disclaimer

This recommendation system is built for educational purposes. The dataset used belongs to Food.com and is distributed through Kaggle under their respective licenses.
