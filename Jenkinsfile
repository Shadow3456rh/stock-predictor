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
        script {
            withCredentials([
                string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                string(credentialsId: 'AWS_SNS_TOPIC_ARN', variable: 'SNS_TOPIC_ARN')
            ]) {
                sh """
                export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                
                aws sns publish --region us-east-1 \
                --topic-arn ${SNS_TOPIC_ARN} \
                --message "✅ SUCCESS: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} completed successfully. \nBuild log: ${env.BUILD_URL}"
                """
            }
        }
    }

    failure {
        script {
            withCredentials([
                string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                string(credentialsId: 'AWS_SNS_TOPIC_ARN', variable: 'SNS_TOPIC_ARN')
            ]) {
                sh """
                export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                
                aws sns publish --region us-east-1 \
                --topic-arn ${SNS_TOPIC_ARN} \
                --message "❌ FAILURE: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} failed. \nBuild log: ${env.BUILD_URL}"
                """
            }
        }
    }
}





}
