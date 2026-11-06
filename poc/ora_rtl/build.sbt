ThisBuild / scalaVersion := "2.12.20"

val spinalVersion = "1.10.2a"

lazy val root = (project in file(".")).
  settings(
    name := "ora-rtl",
    licenses := Seq("BSD-2-Clause-Patent" -> url("https://opensource.org/license/BSD-2-Clause-Patent")),
    libraryDependencies ++= Seq(
      "com.github.spinalhdl" %% "spinalhdl-core" % spinalVersion,
      "com.github.spinalhdl" %% "spinalhdl-lib" % spinalVersion,
      compilerPlugin("com.github.spinalhdl" %% "spinalhdl-idsl-plugin" % spinalVersion)
    ),
    fork := true
  )
