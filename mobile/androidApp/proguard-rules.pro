# Add project specific ProGuard rules here.
-keepattributes Signature
-keepattributes *Annotation*

# Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-keep class kotlinx.serialization.** { *; }
-keepclassmembers class kotlinx.serialization.** { *; }

# Ktor
-keep class io.ktor.** { *; }
-dontwarn io.ktor.**
