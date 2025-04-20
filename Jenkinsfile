pipeline {
    agent any

    triggers {
        cron('H/30 13-20 * * 1-5') 
    }

    environment {
        REPO_URL = 'https://github.com/Shadow3456rh/stock-predictor.git'
        MODEL_FILE = 'models.pkl'
        IMAGE_NAME = 'stock-predictor'
        CONTAINER_NAME = 'stock-predictor'
        AWS_REGION = 'us-east-1'  // ✅ Set region directly here
    }

    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'main', credentialsId: 'GITHUB_PAT', url: "${env.REPO_URL}"
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${env.IMAGE_NAME} ."
            }
        }

        stage('Train Model & Upload to S3') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh """
                        export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                        export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                        docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -v "\$(pwd):/app" ${env.IMAGE_NAME} python3 /app/train_model.py
                    """
                }
            }
        }

        stage('Run Docker Container') {
            steps {
                sh """
                    docker stop ${env.CONTAINER_NAME} || true
                    docker rm ${env.CONTAINER_NAME} || true
                    docker run -d --name ${env.CONTAINER_NAME} -p 5000:5000 ${env.IMAGE_NAME}
                """
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

                        aws sns publish --region ${env.AWS_REGION} \
                        --topic-arn ${SNS_TOPIC_ARN} \
                        --message "SUCCESS: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} completed successfully.\nBuild log: ${env.BUILD_URL}"
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

                        aws sns publish --region ${env.AWS_REGION} \
                        --topic-arn ${SNS_TOPIC_ARN} \
                        --message "FAILURE: Build ${env.JOB_NAME} #${env.BUILD_NUMBER} failed.\nBuild log: ${env.BUILD_URL}"
                    """
                }
            }
        }
    }
}
