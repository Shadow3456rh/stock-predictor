pipeline {
    agent any

    triggers {
        cron('H/30 13-20 * * 1-5') // Run every 30 minutes between 1 PM and 8 PM, Monday to Friday
    }

    environment {
        REPO_URL = 'https://github.com/Shadow3456rh/stock-predictor.git'
        MODEL_FILE = 'models.pkl'
        BUCKET_NAME = 'data-model-bucket-abhishek'
        STOCK_DATA_S3_PREFIX = 'stock_data/'
        MODEL_S3_PREFIX = ''
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
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                    docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -v "$(pwd):/app" stock-predictor python3 /app/fetch_data.py
                    '''
                }
            }
        }

        stage('Upload Stock Data to S3') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                    if [ -d "stock_data" ]; then
                        aws s3 sync stock_data/ s3://${BUCKET_NAME}/${STOCK_DATA_S3_PREFIX} --region us-east-1
                        echo "Uploaded stock_data to s3://${BUCKET_NAME}/${STOCK_DATA_S3_PREFIX}"
                    else
                        echo "stock_data directory not found, skipping upload"
                    fi
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
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                    docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -v "$(pwd):/app" stock-predictor python3 /app/train_model.py
                    '''
                }
            }
        }

        stage('Upload Model to S3') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                    if [ -f "${MODEL_FILE}" ]; then
                        aws s3 cp ${MODEL_FILE} s3://${BUCKET_NAME}/${MODEL_S3_PREFIX}${MODEL_FILE} --region us-east-1
                        echo "Uploaded ${MODEL_FILE} to s3://${BUCKET_NAME}/${MODEL_S3_PREFIX}${MODEL_FILE}"
                    else
                        echo "${MODEL_FILE} not found, skipping upload"
                    fi
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
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
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
                    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                    aws sns publish --region us-east-1 \
                        --topic-arn ${SNS_TOPIC_ARN} \
                        --message "FAILURE: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} failed.\\nBuild log: ${env.BUILD_URL}"
                    """
                }
            }
        }
    }
}
