pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-username/stock-predictor.git'
        MODEL_FILE = 'models.pkl'
    }

    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'main', url: "${REPO_URL}"
            }
        }

        stage('Train Model') {
            steps {
                sh 'python3 train_model.py'
            }
        }

        stage('Commit and Push Model') {
            steps {
                script {
                    sh """
                    git config --global user.email "your-email@example.com"
                    git config --global user.name "Jenkins"
                    git add ${MODEL_FILE}
                    git commit -m "Updated model.pkl - $(date)" || echo "No changes to commit"
                    git push origin main
                    """
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t stock-predictor .'
            }
        }

        stage('Run Docker Container') {
            steps {
                sh 'docker stop stock-predictor || true'
                sh 'docker rm stock-predictor || true'
                sh 'docker run -d --name stock-predictor -p 5000:5000 stock-predictor'
            }
        }
    }

    post {
        failure {
            echo 'Pipeline Failed! Check logs for errors.'
        }
        success {
            echo 'Pipeline executed successfully!'
        }
    }
}
