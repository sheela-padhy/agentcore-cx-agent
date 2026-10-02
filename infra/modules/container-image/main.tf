data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  image_src_path = "${path.root}/${var.relative_image_src_path}"
  image_src_hash = sha512(
    join(
      "",
      # TODO: Find a way to exclude .venv, dist, and potentially other subfolders:
      [for f in fileset(".", "${local.image_src_path}/**") : filesha512(f)]
    )
  )

  image_build_extra_args = "--platform linux/arm64"
  image_build_push_cmd   = <<-EOT
    aws ecr get-login-password | ${var.image_build_tool} login --username AWS \
      --password-stdin ${aws_ecr_repository.ecr_repository.repository_url} &&
    ${var.image_build_tool} build ${local.image_build_extra_args} \
      -t ${aws_ecr_repository.ecr_repository.repository_url}:${var.image_tag} \
      ${local.image_src_path} &&
    ${var.image_build_tool} push ${aws_ecr_repository.ecr_repository.repository_url}:${var.image_tag}
  EOT
}

resource "aws_ecr_repository" "ecr_repository" {
  name                 = var.repository_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "terraform_data" "ecr_image" {
  triggers_replace = [
    aws_ecr_repository.ecr_repository.id,
    var.force_image_rebuild == true ? timestamp() : local.image_src_hash
  ]

  input = "${aws_ecr_repository.ecr_repository.repository_url}:${var.image_tag}"

  provisioner "local-exec" {
    command = local.image_build_push_cmd
  }

  # The CD pipeline (.github/workflows/cd.yml) now builds and pushes images
  # on every merge to main, independently of Terraform, using QEMU/buildx
  # (GitHub's runners are x86_64; this needs an ARM64 image). Terraform's
  # OWN rebuild-on-source-change behavior above conflicts with that: it
  # tries a plain `docker build --platform linux/arm64` with no emulation
  # whenever the source hash differs from what Terraform itself last built
  # - which fails with "exec format error" on GitHub's runners, and is
  # redundant even when it would succeed (CD already handled it). Ignoring
  # changes to the trigger stops Terraform from ever attempting this again;
  # it still creates the resource once on a truly fresh deployment.
  lifecycle {
    ignore_changes = [triggers_replace]
  }
}
