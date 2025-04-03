pipeline {
    agent any
    triggers {
        cron('H/30 * * * *')  
    }

    environment {
        REPO_URL = 'https://github.com/Shadow3456rh/stock-predictor.git'
        MODEL_FILE = 'models.pkl'
        GITHUB_PAT = credentials('GITHUB_PAT')
        RECIPIENTS = 'abhishekangadismailbox@gmail.com'
    }

    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'main', credentialsId: 'GITHUB_PAT', url: "${REPO_URL}"
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t stock-predictor .'
            }
        }

        stage('Train Model') {
            steps {
                sh 'docker run --rm -v "$(pwd):/app" stock-predictor python3 /app/train_model.py'
            }
        }

        stage('Commit and Push Model') {
            steps {
                script {
                    sh '''
                    git config --global user.email "abhishekangadismailbox@gmail.com"
                    git config --global user.name "Jenkins"

                    git add $MODEL_FILE
                    git commit -m "Updated models.pkl - $(date)" || echo "No changes to commit"
                    
                    git push https://Shadow3456rh:$GITHUB_PAT@github.com/Shadow3456rh/stock-predictor.git main
                    '''
                }
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
        emailext subject: "✅ Build SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "Good news! The pipeline ran successfully. \nCheck details at: ${env.BUILD_URL}",
                 to: "abhishekangadismailbox@gmail.com",
                 from: "abhishekangadismailbox@gmail.com",
                 replyTo: "abhishekangadismailbox@gmail.com"
    }
    failure {
        emailext subject: "❌ Build FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "Oops! The pipeline failed. \nCheck logs: ${env.BUILD_URL}",
                 to: "abhishekangadismailbox@gmail.com",
                 from: "abhishekangadismailbox@gmail.com",
                 replyTo: "abhishekangadismailbox@gmail.com"
    }
}
}
