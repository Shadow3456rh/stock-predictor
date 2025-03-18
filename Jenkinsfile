pipeline {
    agent any
    triggers {
        cron('H 0 * * *')  // Runs the pipeline every day at midnight
    }

    environment {
        REPO_URL = 'https://github.com/Shadow3456rh/stock-predictor.git'
        MODEL_FILE = 'models.pkl'
        GITHUB_PAT = credentials('GITHUB_PAT')  // Securely stored in Jenkins Credentials
    }

    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'main', credentialsId: 'GITHUB_PAT', url: "${REPO_URL}"
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
                    sh '''
                    git config --global user.email "your-email@example.com"
                    git config --global user.name "Jenkins"

                    git add $MODEL_FILE
                    git commit -m "Updated models.pkl - $(date)" || echo "No changes to commit"
                    
                    git push https://Shadow3456rh:$GITHUB_PAT@github.com/Shadow3456rh/stock-predictor.git main
                    '''
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
                sh '''
                docker stop stock-predictor || true
                docker rm stock-predictor || true
                docker run -d --name stock-predictor -p 5000:5000 stock-predictor
                '''
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline executed successfully!'
        }
        failure {
            echo '❌ Pipeline Failed! Check logs for errors.'
        }
    }
}
