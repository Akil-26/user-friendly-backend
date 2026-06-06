pipeline {
    agent any

    environment {
        RAILWAY_TOKEN = credentials('railway-token')
    }

    stages {

        stage('Checkout') {
            steps {
                echo '📥 Pulling latest code...'
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                echo '🐍 Setting up Python environment...'
                bat 'python -m venv venv'
                bat 'venv\\Scripts\\activate && pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                echo '🧪 Running tests...'
                bat 'venv\\Scripts\\activate && pytest tests/ -v --tb=short'
            }
        }

        stage('Deploy to Railway') {
            when {
                branch 'main'  // only deploy from main branch
            }
            steps {
                echo '🚀 Deploying to Railway...'
                bat '''
                    npm install -g @railway/cli
                    railway up --service user-friendly-backend
                '''
            }
        }

    }

    post {
        success {
            echo '✅ Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed — check the logs above'
        }
    }
}