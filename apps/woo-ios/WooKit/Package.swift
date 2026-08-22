// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "WooKit",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "WooKit", targets: ["WooKit"])
    ],
    targets: [
        .target(name: "WooKit"),
        .testTarget(name: "WooKitTests", dependencies: ["WooKit"])
    ]
)
