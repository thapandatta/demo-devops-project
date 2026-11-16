moved {
  from = aws_iam_role.ec2_ssm
  to   = module.app_server.aws_iam_role.ec2_ssm
}

moved {
  from = aws_iam_role_policy_attachment.ssm_core
  to   = module.app_server.aws_iam_role_policy_attachment.ssm_core
}

moved {
  from = aws_iam_instance_profile.ec2_ssm
  to   = module.app_server.aws_iam_instance_profile.ec2_ssm
}

moved {
  from = aws_security_group.web
  to   = module.app_server.aws_security_group.web
}

moved {
  from = aws_instance.web
  to   = module.app_server.aws_instance.web
}

moved {
  from = aws_dynamodb_table.items
  to   = module.app_server.aws_dynamodb_table.items
}

moved {
  from = aws_iam_role_policy.app_dynamodb
  to   = module.app_server.aws_iam_role_policy.app_dynamodb
}

# ---------- cicd-access module ----------
moved {
  from = aws_iam_openid_connect_provider.github
  to   = module.cicd_access.aws_iam_openid_connect_provider.github
}

moved {
  from = aws_iam_role.github_actions
  to   = module.cicd_access.aws_iam_role.github_actions
}

moved {
  from = aws_iam_role_policy.deploy
  to   = module.cicd_access.aws_iam_role_policy.deploy
}