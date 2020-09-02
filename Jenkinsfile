#!/usr/bin/env groovy
import java.io.File;
node('Jenkins-Backend-Slave') {
    timestamps {
      properties([
        buildDiscarder(logRotator(
          artifactDaysToKeepStr: '',
          artifactNumToKeepStr: '',
          daysToKeepStr: '60',
          numToKeepStr: '10'
        )),
        parameters([
          booleanParam(
            defaultValue: false,
            description: 'Check this box if you want to skip the test case execution for the current build', name: 'skipTestsFlag')
        ]),
        disableConcurrentBuilds()
      ])
      timeout(activity: true, time: 5) {
        stage('Code Checkout'){
          try{
            cleanWs()
            checkout([
              $class: 'GitSCM',
              branches: scm.branches,
              extensions: scm.extensions + [[$class: 'CleanCheckout']] +
              [[$class: 'LocalBranch', localBranch: "${env.BRANCH_NAME}" ]],
              userRemoteConfigs: scm.userRemoteConfigs
            ])
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'is_devops_prod',
              accessKeyVariable: 'Dev_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Dev_AWS_SECRET_ACCESS_KEY'
              ],
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'ab1d6684-0bcf-4869-aed5-c22e607ba742',
              accessKeyVariable: 'Prod_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Prod_AWS_SECRET_ACCESS_KEY'
              ]]){
                sh """
                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile devProfile
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile devProfile
                  sudo aws configure set region us-east-1 --profile devProfile
                  sudo aws configure set aws_access_key_id ${env.Prod_AWS_ACCESS_KEY_ID} --profile prodProfile
                  sudo aws configure set aws_secret_access_key ${env.Prod_AWS_SECRET_ACCESS_KEY} --profile prodProfile
                  sudo aws configure set region us-east-1 --profile prodProfile
                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile default
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile default
                  sudo aws configure set region us-east-1 --profile default
                """
              }
          }
          catch(e){
            echo "Code Checkout has failed : ${e}"
            Notify()
            throw(e)
          }
        }

        stage('Publish ECR Images'){
          try{
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'is_devops_prod',
              accessKeyVariable: 'Dev_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Dev_AWS_SECRET_ACCESS_KEY'
              ],
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'ab1d6684-0bcf-4869-aed5-c22e607ba742',
              accessKeyVariable: 'Prod_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Prod_AWS_SECRET_ACCESS_KEY'
              ]]){
                sh """
                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile devProfile
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile devProfile
                  sudo aws configure set region us-east-1 --profile devProfile

                  sudo aws configure set aws_access_key_id ${env.Prod_AWS_ACCESS_KEY_ID} --profile prodProfile
                  sudo aws configure set aws_secret_access_key ${env.Prod_AWS_SECRET_ACCESS_KEY} --profile prodProfile
                  sudo aws configure set region us-east-1 --profile prodProfile

                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile default
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile default
                  sudo aws configure set region us-east-1 --profile default

                  sudo chown -R ubuntu:ubuntu ~/.aws
                  sudo chown -R ubuntu:ubuntu ~/.npm
                  sudo chown -R ubuntu:ubuntu ~/.config

                  sudo snap install docker
                  sudo chmod 777 /var/run/docker.sock || true
                """

                ecr_login = sh(script: "/bin/bash -c \'aws ecr get-login-password --region us-east-1 | /snap/bin/docker login --username AWS --password-stdin 691195436300.dkr.ecr.us-east-1.amazonaws.com/k8s-sqs-autoscaler\'", returnStdout: true)
                echo ecr_login
                sh """
                  #Package casemaker images
                  /snap/bin/docker build -t k8s-sqs-autoscaler:${env.BRANCH_NAME} .
                  /snap/bin/docker tag k8s-sqs-autoscaler:${env.BRANCH_NAME} 691195436300.dkr.ecr.us-east-1.amazonaws.com/k8s-sqs-autoscaler:${env.BRANCH_NAME}
                  /snap/bin/docker push 691195436300.dkr.ecr.us-east-1.amazonaws.com/k8s-sqs-autoscaler:${env.BRANCH_NAME}
                """
            }
          }
          catch(e){
            echo "ECR Image creation has failed : ${e}"
            Notify()
            throw(e)
          }
        }
      }
    }
}
def Notify(){
  emailext body: "Please check ${env.BUILD_URL} for more details on this",
           recipientProviders: [culprits()],
           subject: "Core Backend build has failed for ${env.BRANCH_NAME} branch"
}

def bulk_copy(list) {
    sh "echo Going to echo a list"
    for (int i = 0; i < list.size(); i++) {
        sh """mkdir -p ${env.WORKSPACE}/${list[i]}
              touch ${env.WORKSPACE}/${list[i]}/is_docker.pem
              cat ${env.ssh_key} | tee -a ${env.WORKSPACE}/${list[i]}/is_docker.pem > /dev/null
              cp -r ${env.WORKSPACE}/core_services ${env.WORKSPACE}/${list[i]}/
        """
    }
}

def env_build(env_list) {
  sh """
        #Deploying lambda layer for all the environments and applications
  """
  for (int i = 0; i < env_list.size(); i++) {
      sh """
        cd ${env.WORKSPACE}
        export PATH=$PATH:/snap/bin
        sudo chmod 777 /var/run/docker.sock || true
        ./deploy-app-layer.sh --app labelmaker --env ${env_list[i]} --alias ${env_list[i]};
        ./deploy-python-layer.sh --app labelmaker --env ${env_list[i]} --alias ${env_list[i]} --ssh-key ${env.ssh_key};
      """
  }
}
