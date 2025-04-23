pipeline {
    agent any

    triggers {
        cron('H/30 13-20 * * 1-5') 
    }

    environment {
        REPO_URL = 'https://github.com/Shadow3456rh/stock-predictor.git'
        BUCKET_NAME = 'data-model-bucket-abhishek'
        STOCK_DATA_S3_PREFIX = 'stock_data/'
        MODEL_S3_PREFIX = 'models/'
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

        stage('Fetch Stock Data') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                    docker run --rm \
                        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
                        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
                        stock-predictor python3 /app/fetch_data.py
                    '''
                }
            }
        }

        stage('Train Model') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                    docker run --rm \
                        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
                        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
                        stock-predictor python3 /app/train_model.py
                    '''
                }
            }
        }

        stage('Run Docker Container') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                    docker stop stock-predictor || true
                    docker rm stock-predictor || true
                    docker run -d --name stock-predictor \
                        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
                        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
                        -p 5000:5000 stock-predictor
                    '''
                }
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
                    aws sns publish --region us-east-1 \
                        --topic-arn ${SNS_TOPIC_ARN} \
                        --message "SUCCESS: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} completed successfully.\\nBuild log: ${env.BUILD_URL}"
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
                    aws sns publish --region us-east-1 \
                        --topic-arn ${SNS_TOPIC_ARN} \
                        --message "FAILURE: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} failed.\\nBuild log: ${env.BUILD_URL}"
                    """
                }
            }
        }
    }
}
